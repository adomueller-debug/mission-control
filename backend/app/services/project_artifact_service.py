from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import shutil
from pathlib import Path
from typing import Any

import requests
from sqlalchemy import select

from backend.app.core.workspace_security import resolve_workspace_path
from backend.app.database.database import SessionLocal
from backend.app.models.project import Project, ProjectArtifact, ProjectTask
from backend.app.models.run import AgentRun


MAX_SYNC_BYTES = 20 * 1024 * 1024


def artifact_to_dict(artifact: ProjectArtifact) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "project_id": artifact.project_id,
        "task_id": artifact.task_id,
        "run_id": artifact.run_id,
        "name": artifact.name,
        "artifact_type": artifact.artifact_type,
        "media_type": artifact.media_type,
        "size_bytes": artifact.size_bytes,
        "sync_status": artifact.sync_status,
        "external_url": artifact.external_url or None,
        "preview_available": artifact.artifact_type == "website",
        "created_at": artifact.created_at.isoformat(),
    }


def _safe_name(value: str, fallback: str = "artifact") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-.")
    return normalized[:120] or fallback


def _artifact_root() -> Path:
    configured = os.getenv("MISSION_CONTROL_ARTIFACT_ROOT", "").strip()
    root = Path(configured) if configured else Path.cwd() / "data" / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


class ProjectArtifactService:
    def archive_completed_task(
        self,
        db,
        project: Project,
        task: ProjectTask,
        run: AgentRun,
    ) -> tuple[list[ProjectArtifact], bool]:
        existing = db.scalars(
            select(ProjectArtifact).where(ProjectArtifact.run_id == run.id)
        ).all()
        if existing:
            return list(existing), False
        try:
            result = json.loads(run.result or "{}")
        except json.JSONDecodeError:
            result = {"summary": run.result}
        if not isinstance(result, dict):
            result = {"result": result}

        bundle_root = _artifact_root() / project.id / task.id / run.id
        files_root = bundle_root / "files"
        documents_root = bundle_root / "documents"
        bundle_root.mkdir(parents=True, exist_ok=True)
        artifacts: list[ProjectArtifact] = []
        copied_files: list[tuple[str, Path]] = []

        for relative in result.get("files", []):
            if not isinstance(relative, str):
                continue
            try:
                source = resolve_workspace_path(run.workspace, relative, must_exist=True)
            except (OSError, ValueError):
                continue
            if not source.is_file():
                continue
            target = files_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied_files.append((relative, target))
            artifacts.append(
                ProjectArtifact(
                    project_id=project.id,
                    task_id=task.id,
                    run_id=run.id,
                    artifact_key=f"file:{relative}",
                    name=Path(relative).name,
                    artifact_type="file",
                    storage_path=str(target),
                    media_type=mimetypes.guess_type(target.name)[0]
                    or "application/octet-stream",
                    size_bytes=target.stat().st_size,
                    sync_status="pending" if os.getenv("GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID") else "local",
                )
            )

        index_files = [item for item in copied_files if Path(item[0]).name.lower() == "index.html"]
        if index_files:
            relative, target = index_files[0]
            artifacts.insert(
                0,
                ProjectArtifact(
                    project_id=project.id,
                    task_id=task.id,
                    run_id=run.id,
                    artifact_key=f"website:{Path(relative).parent.as_posix()}",
                    name=f"{task.title} – Website-Vorschau",
                    artifact_type="website",
                    storage_path=str(target.parent),
                    entry_path=target.name,
                    media_type="text/html",
                    size_bytes=sum(file.stat().st_size for _, file in copied_files),
                    sync_status="pending" if os.getenv("GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID") else "local",
                ),
            )

        for index, item in enumerate(result.get("artifacts", []), start=1):
            if not isinstance(item, dict) or not str(item.get("content", "")).strip():
                continue
            title = str(item.get("title") or f"Artefakt {index}")
            artifact_type = str(item.get("artifact_type") or "document")
            target = documents_root / f"{index:02d}-{_safe_name(title)}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(item["content"]), encoding="utf-8")
            artifacts.append(
                ProjectArtifact(
                    project_id=project.id,
                    task_id=task.id,
                    run_id=run.id,
                    artifact_key=f"document:{index}:{_safe_name(title)}",
                    name=title,
                    artifact_type=artifact_type,
                    storage_path=str(target),
                    media_type="text/markdown",
                    size_bytes=target.stat().st_size,
                    sync_status="pending" if os.getenv("GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID") else "local",
                )
            )

        manifest = bundle_root / "result.json"
        manifest.write_text(
            json.dumps(
                {
                    "project": {"id": project.id, "name": project.name, "goal": project.goal},
                    "task": {"id": task.id, "title": task.title, "type": task.task_type},
                    "run_id": run.id,
                    "result": result,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        artifacts.append(
            ProjectArtifact(
                project_id=project.id,
                task_id=task.id,
                run_id=run.id,
                artifact_key="manifest",
                name=f"{task.title} – Ergebnisbericht",
                artifact_type="report",
                storage_path=str(manifest),
                media_type="application/json",
                size_bytes=manifest.stat().st_size,
                sync_status="pending" if os.getenv("GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID") else "local",
            )
        )
        db.add_all(artifacts)
        db.flush()
        return artifacts, True

    def list_project(self, project_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            artifacts = db.scalars(
                select(ProjectArtifact)
                .where(ProjectArtifact.project_id == project_id)
                .order_by(ProjectArtifact.created_at.desc())
            ).all()
            return [artifact_to_dict(item) for item in artifacts]

    def get(self, artifact_id: str) -> ProjectArtifact | None:
        with SessionLocal() as db:
            artifact = db.get(ProjectArtifact, artifact_id)
            if artifact is not None:
                db.expunge(artifact)
            return artifact

    def sync_project(self, project_id: str) -> dict[str, Any]:
        webhook = os.getenv("N8N_PROJECT_DELIVERY_WEBHOOK_URL", "").strip()
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise KeyError(project_id)
            artifacts = db.scalars(
                select(ProjectArtifact).where(ProjectArtifact.project_id == project_id)
            ).all()
            if not webhook:
                return {
                    "status": "local",
                    "artifact_count": len(artifacts),
                    "message": "Lokal gesichert; n8n-Drive-Webhook ist noch nicht konfiguriert.",
                }
            payload_artifacts = []
            total_bytes = 0
            for artifact in artifacts:
                path = Path(artifact.storage_path)
                if not path.is_file() or artifact.artifact_type == "website":
                    continue
                total_bytes += path.stat().st_size
                if total_bytes > MAX_SYNC_BYTES:
                    raise ValueError("Projektartefakte überschreiten das 20-MB-Synchronisationslimit.")
                payload_artifacts.append(
                    {
                        "id": artifact.id,
                        "key": artifact.artifact_key,
                        "name": artifact.name,
                        "media_type": artifact.media_type,
                        "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                    }
                )
            response = requests.post(
                webhook,
                json={
                    "project": {"id": project.id, "name": project.name, "goal": project.goal},
                    "root_folder_id": os.getenv("GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID", ""),
                    "spreadsheet_id": os.getenv("GOOGLE_SHEETS_CRM_SPREADSHEET_ID", ""),
                    "artifacts": payload_artifacts,
                },
                timeout=(5, 60),
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
            links = data.get("artifact_urls", {}) if isinstance(data, dict) else {}
            for artifact in artifacts:
                artifact.sync_status = "synced"
                artifact.external_url = str(links.get(artifact.artifact_key, ""))
            db.commit()
            return {"status": "synced", "artifact_count": len(artifacts)}


project_artifact_service = ProjectArtifactService()
