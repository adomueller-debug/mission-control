from __future__ import annotations

import json
import threading
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

import requests
from sqlalchemy import select

from backend.app.core.workspace_security import resolve_workspace
from backend.app.database.database import SessionLocal
from backend.app.models.project import Project, ProjectArtifact, ProjectTask
from backend.app.models.run import AgentRun
from backend.app.services.agent_catalog import get_agent
from backend.app.services.run_service import run_service
from backend.app.services.project_artifact_service import (
    artifact_to_dict,
    project_artifact_service,
)


PROJECT_STATUSES = {"idea", "planning", "active", "paused", "completed", "archived"}
TASK_STATUSES = {
    "backlog",
    "planned",
    "queued",
    "in_progress",
    "blocked",
    "review",
    "completed",
    "cancelled",
}
TASK_TYPES = {"general", "coding", "research", "design", "automation", "business", "data", "security", "devops"}
EXECUTABLE_TASK_TYPES = TASK_TYPES
AUTOPILOT_RUN_OPTIONS: dict[str, Any] = {
    "publish": False,
    "timeout_seconds": 1200,
    "max_tool_calls": 50,
    "max_repair_attempts": 5,
}
RUN_TO_TASK_STATUS = {
    "queued": "queued",
    "planning": "in_progress",
    "executing": "in_progress",
    "validating": "review",
    "publishing": "review",
    "completed": "completed",
    "failed": "blocked",
    "cancelled": "cancelled",
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _task_dict(task: ProjectTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "task_type": task.task_type,
        "assigned_agent": task.assigned_agent,
        "run_id": task.run_id,
        "due_at": _iso(task.due_at),
        "result": json.loads(task.result) if task.result else None,
        "dependencies": json.loads(task.dependencies or "[]"),
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
        "executable": task.task_type in EXECUTABLE_TASK_TYPES,
    }


def _project_dict(
    project: Project,
    tasks: list[ProjectTask],
    artifacts: list[ProjectArtifact] | None = None,
) -> dict[str, Any]:
    counts = Counter(task.status for task in tasks)
    relevant = [task for task in tasks if task.status != "cancelled"]
    completed = counts["completed"]
    progress = round((completed / len(relevant)) * 100) if relevant else 0
    active_agents = sorted(
        {
            task.assigned_agent
            for task in tasks
            if task.assigned_agent
            and task.status in {"queued", "in_progress", "blocked", "review"}
        }
    )
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "goal": project.goal,
        "category": project.category,
        "status": project.status,
        "workspace": project.workspace,
        "owner_agent": project.owner_agent,
        "deadline": _iso(project.deadline),
        "budget_cents": project.budget_cents,
        "revenue_target_cents": project.revenue_target_cents,
        "autopilot_enabled": project.autopilot_enabled,
        "created_at": _iso(project.created_at),
        "updated_at": _iso(project.updated_at),
        "progress": progress,
        "task_counts": dict(counts),
        "active_agents": active_agents,
        "tasks": [_task_dict(task) for task in tasks],
        "artifacts": [artifact_to_dict(item) for item in artifacts or []],
    }


def _compact_task_result(task: ProjectTask) -> str:
    try:
        payload = json.loads(task.result)
    except (json.JSONDecodeError, TypeError):
        return task.result[:2_000]
    if not isinstance(payload, dict):
        return str(payload)[:2_000]
    summary = str(payload.get("summary") or "")[:1_500]
    findings = payload.get("findings") or []
    concise_findings = [str(item)[:300] for item in findings[:3]]
    parts = [summary] if summary else []
    if concise_findings:
        parts.append("Kernaussagen: " + " | ".join(concise_findings))
    return "\n".join(parts)[:2_500]


class ProjectService:
    def __init__(self) -> None:
        self._autopilot_projects: set[str] = set()
        self._autopilot_lock = threading.Lock()

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        goal: str = "",
        category: str = "general",
        status: str = "idea",
        workspace: str,
        owner_agent: str | None = None,
        deadline: datetime | None = None,
        budget_cents: int = 0,
        revenue_target_cents: int = 0,
    ) -> dict[str, Any]:
        self._validate_project_status(status)
        self._validate_project_controls(owner_agent, budget_cents, revenue_target_cents)
        root = resolve_workspace(workspace)
        project = Project(
            name=name.strip(),
            description=description.strip(),
            goal=goal.strip(),
            category=category.strip().lower() or "general",
            status=status,
            workspace=str(root),
            owner_agent=owner_agent,
            deadline=deadline,
            budget_cents=budget_cents,
            revenue_target_cents=revenue_target_cents,
        )
        with SessionLocal() as db:
            db.add(project)
            db.commit()
            db.refresh(project)
            return _project_dict(project, [])

    def list_projects(self) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            self._sync_linked_tasks(db)
            projects = db.scalars(
                select(Project).order_by(Project.updated_at.desc())
            ).all()
            tasks = db.scalars(
                select(ProjectTask).order_by(ProjectTask.priority, ProjectTask.created_at)
            ).all()
            artifacts = db.scalars(
                select(ProjectArtifact).order_by(ProjectArtifact.created_at.desc())
            ).all()
            grouped: dict[str, list[ProjectTask]] = defaultdict(list)
            grouped_artifacts: dict[str, list[ProjectArtifact]] = defaultdict(list)
            for task in tasks:
                grouped[task.project_id].append(task)
            for artifact in artifacts:
                grouped_artifacts[artifact.project_id].append(artifact)
            return [
                _project_dict(
                    project,
                    grouped[project.id],
                    grouped_artifacts[project.id],
                )
                for project in projects
            ]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with SessionLocal() as db:
            self._sync_linked_tasks(db)
            project = db.get(Project, project_id)
            if project is None:
                return None
            tasks = db.scalars(
                select(ProjectTask)
                .where(ProjectTask.project_id == project_id)
                .order_by(ProjectTask.priority, ProjectTask.created_at)
            ).all()
            artifacts = db.scalars(
                select(ProjectArtifact)
                .where(ProjectArtifact.project_id == project_id)
                .order_by(ProjectArtifact.created_at.desc())
            ).all()
            return _project_dict(project, list(tasks), list(artifacts))

    def update_project(self, project_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        if "status" in fields:
            self._validate_project_status(fields["status"])
        if "workspace" in fields:
            fields["workspace"] = str(resolve_workspace(fields["workspace"]))
        if any(key in fields for key in ("owner_agent", "budget_cents", "revenue_target_cents")):
            current = self.get_project(project_id)
            if current is None:
                return None
            self._validate_project_controls(
                fields.get("owner_agent", current["owner_agent"]),
                fields.get("budget_cents", current["budget_cents"]),
                fields.get("revenue_target_cents", current["revenue_target_cents"]),
            )
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                return None
            for key, value in fields.items():
                if value is not None:
                    setattr(project, key, value.strip() if isinstance(value, str) else value)
            project.updated_at = datetime.now(UTC)
            db.commit()
        return self.get_project(project_id)

    def archive_project(self, project_id: str) -> dict[str, Any]:
        run_ids: list[str] = []
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)
            project.status = "archived"
            project.autopilot_enabled = False
            project.updated_at = datetime.now(UTC)
            active_tasks = db.scalars(
                select(ProjectTask).where(
                    ProjectTask.project_id == project_id,
                    ProjectTask.status.in_({"queued", "in_progress", "review"}),
                )
            ).all()
            for task in active_tasks:
                task.status = "cancelled"
                task.updated_at = project.updated_at
                if task.run_id:
                    run_ids.append(task.run_id)
            db.commit()
        for run_id in run_ids:
            run_service.cancel(run_id)
        project_data = self.get_project(project_id)
        if project_data is None:
            raise KeyError(project_id)
        return project_data

    def restore_project(self, project_id: str) -> dict[str, Any]:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)
            if project.status != "archived":
                raise ValueError("Nur archivierte Projekte können wiederhergestellt werden.")
            project.status = "paused"
            project.autopilot_enabled = False
            project.updated_at = datetime.now(UTC)
            db.commit()
        project_data = self.get_project(project_id)
        if project_data is None:
            raise KeyError(project_id)
        return project_data

    def create_task(
        self,
        project_id: str,
        *,
        title: str,
        description: str = "",
        status: str = "backlog",
        priority: int = 3,
        task_type: str = "general",
        assigned_agent: str | None = None,
        due_at: datetime | None = None,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any] | None:
        self._validate_task(status, priority, task_type, assigned_agent)
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                return None
            task = ProjectTask(
                project_id=project_id,
                title=title.strip(),
                description=description.strip(),
                status=status,
                priority=priority,
                task_type=task_type,
                assigned_agent=assigned_agent,
                due_at=due_at,
                dependencies=json.dumps(dependencies or []),
            )
            project.updated_at = datetime.now(UTC)
            db.add(task)
            db.commit()
            db.refresh(task)
            return _task_dict(task)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with SessionLocal() as db:
            self._sync_linked_tasks(db)
            task = db.get(ProjectTask, task_id)
            return _task_dict(task) if task else None

    def update_task(self, task_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get_task(task_id)
        if current is None:
            return None
        status = fields.get("status", current["status"])
        priority = fields.get("priority", current["priority"])
        task_type = fields.get("task_type", current["task_type"])
        assigned_agent = fields.get("assigned_agent", current["assigned_agent"])
        self._validate_task(status, priority, task_type, assigned_agent)
        with SessionLocal() as db:
            task = db.get(ProjectTask, task_id)
            if task is None:
                return None
            for key, value in fields.items():
                setattr(task, key, value.strip() if isinstance(value, str) else value)
            task.updated_at = datetime.now(UTC)
            project = db.get(Project, task.project_id)
            if project:
                project.updated_at = task.updated_at
            db.commit()
            db.refresh(task)
            return _task_dict(task)

    def start_task(
        self,
        task_id: str,
        *,
        publish: bool,
        timeout_seconds: int,
        max_tool_calls: int,
        max_repair_attempts: int,
    ) -> dict[str, Any]:
        with SessionLocal() as db:
            task = db.get(ProjectTask, task_id)
            if task is None:
                raise KeyError(task_id)
            project = db.get(Project, task.project_id)
            if project is None:
                raise KeyError(task.project_id)
            if task.run_id:
                raise ValueError("Diese Aufgabe ist bereits mit einem Run verbunden.")
            prior_results = db.scalars(
                select(ProjectTask)
                .where(
                    ProjectTask.project_id == project.id,
                    ProjectTask.status == "completed",
                    ProjectTask.result != "",
                )
                .order_by(ProjectTask.updated_at)
            ).all()
            context = "\n\n".join(
                f"Vorheriges Ergebnis – {item.title}:\n{_compact_task_result(item)}"
                for item in prior_results[-3:]
            )[:8_000]
            context_block = (
                f"\n\nProjektkontext aus abgeschlossenen Aufgaben:\n{context}"
                if context
                else ""
            )
            prompt = (
                f"Projekt: {project.name}\nProjektziel: {project.goal or '-'}\n\n"
                f"Aufgabe: {task.title}\n{task.description}"
                f"{context_block}"
            )
            workspace = project.workspace
            task_type = task.task_type

        run = run_service.create(
            task=prompt,
            workspace=workspace,
            publish=publish if task_type == "coding" else False,
            timeout_seconds=timeout_seconds,
            max_tool_calls=max_tool_calls,
            max_repair_attempts=max_repair_attempts,
            run_kind="coding" if task_type == "coding" else f"task:{task_type}",
            workstream="project",
            start=False,
        )
        with SessionLocal() as db:
            task = db.get(ProjectTask, task_id)
            if task is None:
                raise KeyError(task_id)
            task.run_id = run["id"]
            task.status = "queued"
            task.updated_at = datetime.now(UTC)
            db.commit()
        run_service.start(run["id"])
        return {"task": self.get_task(task_id), "run": run}

    def enable_autopilot(self, project_id: str) -> dict[str, Any]:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)
            blocked_tasks = db.scalars(
                select(ProjectTask).where(
                    ProjectTask.project_id == project_id,
                    ProjectTask.status.in_({"blocked", "cancelled"}),
                )
            ).all()
            for task in blocked_tasks:
                task.status = "planned"
                task.run_id = None
                task.updated_at = datetime.now(UTC)
            project.autopilot_enabled = True
            project.status = "active"
            project.updated_at = datetime.now(UTC)
            db.commit()
        self._spawn_autopilot(project_id)
        project_data = self.get_project(project_id)
        if project_data is None:
            raise KeyError(project_id)
        return project_data

    def disable_autopilot(self, project_id: str) -> dict[str, Any]:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)
            project.autopilot_enabled = False
            project.status = "paused"
            project.updated_at = datetime.now(UTC)
            db.commit()
        project_data = self.get_project(project_id)
        if project_data is None:
            raise KeyError(project_id)
        return project_data

    def recover_autopilots(self) -> None:
        with SessionLocal() as db:
            project_ids = list(
                db.scalars(
                    select(Project.id).where(
                        Project.autopilot_enabled.is_(True),
                        Project.status == "active",
                    )
                ).all()
            )
        for project_id in project_ids:
            self._spawn_autopilot(project_id)

    def _spawn_autopilot(self, project_id: str) -> None:
        with self._autopilot_lock:
            if project_id in self._autopilot_projects:
                return
            self._autopilot_projects.add(project_id)
        thread = threading.Thread(
            target=self._autopilot_loop,
            args=(project_id,),
            daemon=True,
            name=f"mission-autopilot-{project_id[:8]}",
        )
        thread.start()

    def _autopilot_loop(self, project_id: str) -> None:
        try:
            while True:
                project = self.get_project(project_id)
                if (
                    project is None
                    or not project["autopilot_enabled"]
                    or project["status"] != "active"
                ):
                    return

                tasks = project["tasks"]
                if any(
                    task["status"] in {"queued", "in_progress", "review"}
                    for task in tasks
                ):
                    time.sleep(2)
                    continue

                if any(task["status"] == "blocked" for task in tasks):
                    self.disable_autopilot(project_id)
                    return

                pending = [
                    task
                    for task in tasks
                    if task["status"] in {"backlog", "planned"}
                    and task["executable"]
                    and not task["run_id"]
                ]
                if not pending:
                    self.update_project(
                        project_id,
                        {"status": "completed", "autopilot_enabled": False},
                    )
                    try:
                        project_artifact_service.sync_project(project_id)
                    except (OSError, ValueError, requests.RequestException):
                        # Local persistence is authoritative. External Drive sync can
                        # be retried from the dashboard without failing the project.
                        pass
                    return

                completed_ids = {
                    task["id"] for task in tasks if task["status"] == "completed"
                }
                ready = [
                    task
                    for task in pending
                    if set(task["dependencies"]).issubset(completed_ids)
                ]
                if not ready:
                    self.disable_autopilot(project_id)
                    return

                next_task = min(
                    ready,
                    key=lambda task: (task["priority"], task["created_at"]),
                )
                try:
                    self.start_task(next_task["id"], **AUTOPILOT_RUN_OPTIONS)
                except ValueError:
                    # Another safe workspace run may still be finishing.
                    time.sleep(2)
                    continue
                time.sleep(1)
        finally:
            with self._autopilot_lock:
                self._autopilot_projects.discard(project_id)

    @staticmethod
    def _sync_linked_tasks(db) -> None:
        tasks = db.scalars(
            select(ProjectTask).where(ProjectTask.run_id.is_not(None))
        ).all()
        changed = False
        for task in tasks:
            run = db.get(AgentRun, task.run_id)
            if run is None:
                continue
            project = db.get(Project, task.project_id)
            if project is None or project.status != "archived":
                status = RUN_TO_TASK_STATUS.get(run.status, task.status)
                if status != task.status:
                    task.status = status
                    task.updated_at = datetime.now(UTC)
                    changed = True
            if run.status == "completed" and run.result and run.result != task.result:
                task.result = run.result
                task.updated_at = datetime.now(UTC)
                changed = True
            if run.status == "completed" and run.result:
                if project is not None:
                    _, created = project_artifact_service.archive_completed_task(
                        db, project, task, run
                    )
                    changed = changed or created
        if changed:
            db.commit()

    @staticmethod
    def _validate_project_status(status: str) -> None:
        if status not in PROJECT_STATUSES:
            raise ValueError(f"Ungültiger Projektstatus: {status}")

    @staticmethod
    def _validate_task(
        status: str, priority: int, task_type: str, assigned_agent: str | None
    ) -> None:
        if status not in TASK_STATUSES:
            raise ValueError(f"Ungültiger Aufgabenstatus: {status}")
        if priority not in {1, 2, 3, 4, 5}:
            raise ValueError("Priorität muss zwischen 1 und 5 liegen.")
        if task_type not in TASK_TYPES:
            raise ValueError(f"Ungültiger Aufgabentyp: {task_type}")
        if assigned_agent and get_agent(assigned_agent) is None:
            raise ValueError(f"Unbekannter Agent: {assigned_agent}")

    @staticmethod
    def _validate_project_controls(
        owner_agent: str | None, budget_cents: int, revenue_target_cents: int
    ) -> None:
        if owner_agent and get_agent(owner_agent) is None:
            raise ValueError(f"Unbekannter Projekt-Lead: {owner_agent}")
        if budget_cents < 0 or revenue_target_cents < 0:
            raise ValueError("Budget und Umsatz-Ziel dürfen nicht negativ sein.")


project_service = ProjectService()
