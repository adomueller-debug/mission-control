from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.runs import RunOptions
from backend.app.services.project_service import project_service

router = APIRouter(prefix="/api/v1", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=10_000)
    goal: str = Field(default="", max_length=10_000)
    category: str = Field(default="general", min_length=1, max_length=50)
    status: str = "idea"
    workspace: str = Field(default_factory=lambda: str(Path.cwd()))
    owner_agent: str | None = None
    deadline: datetime | None = None
    budget_cents: int = Field(default=0, ge=0)
    revenue_target_cents: int = Field(default=0, ge=0)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    goal: str | None = Field(default=None, max_length=10_000)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    status: str | None = None
    workspace: str | None = None
    owner_agent: str | None = None
    deadline: datetime | None = None
    budget_cents: int | None = Field(default=None, ge=0)
    revenue_target_cents: int | None = Field(default=None, ge=0)


class CreateProjectTaskRequest(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=20_000)
    status: str = "backlog"
    priority: int = Field(default=3, ge=1, le=5)
    task_type: str = "general"
    assigned_agent: str | None = None
    due_at: str | None = None


class UpdateProjectTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=20_000)
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    task_type: str | None = None
    assigned_agent: str | None = None


class StartProjectTaskRequest(BaseModel):
    options: RunOptions = Field(default_factory=RunOptions)


@router.get("/projects")
def list_projects():
    return project_service.list_projects()


@router.post("/projects", status_code=201)
def create_project(request: CreateProjectRequest):
    try:
        return project_service.create_project(**request.model_dump())
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    project = project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


@router.patch("/projects/{project_id}")
def update_project(project_id: str, request: UpdateProjectRequest):
    try:
        project = project_service.update_project(
            project_id, request.model_dump(exclude_unset=True)
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


@router.post("/projects/{project_id}/tasks", status_code=201)
def create_project_task(project_id: str, request: CreateProjectTaskRequest):
    payload = request.model_dump(exclude={"due_at"})
    if request.due_at:
        try:
            payload["due_at"] = datetime.fromisoformat(request.due_at)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Ungültiges Fälligkeitsdatum") from exc
    try:
        task = project_service.create_task(project_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return task


@router.get("/project-tasks/{task_id}")
def get_project_task(task_id: str):
    task = project_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
    return task


@router.patch("/project-tasks/{task_id}")
def update_project_task(task_id: str, request: UpdateProjectTaskRequest):
    try:
        task = project_service.update_task(
            task_id, request.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
    return task


@router.post("/project-tasks/{task_id}/run", status_code=202)
def start_project_task(task_id: str, request: StartProjectTaskRequest):
    try:
        return project_service.start_task(task_id, **request.options.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden") from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/projects/{project_id}/autopilot/start", status_code=202)
def start_project_autopilot(project_id: str):
    try:
        return project_service.enable_autopilot(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden") from exc


@router.post("/projects/{project_id}/autopilot/stop")
def stop_project_autopilot(project_id: str):
    try:
        return project_service.disable_autopilot(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden") from exc
