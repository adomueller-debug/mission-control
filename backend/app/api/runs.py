from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.app.core.workspace_security import resolve_workspace_path
from backend.app.services.agent_catalog import (
    AGENT_STATUS_DEFINITIONS,
    agent_roster,
    get_agent,
)
from backend.app.services.agent_team import agent_team
from backend.app.services.change_service import change_service
from backend.app.services.coder import MODEL
from backend.app.services.run_service import run_service

router = APIRouter(prefix="/api/v1", tags=["Runs"])


class RunOptions(BaseModel):
    timeout_seconds: int = Field(default=1200, ge=30, le=7200)
    max_tool_calls: int = Field(default=50, ge=1, le=500)
    max_repair_attempts: int = Field(default=5, ge=0, le=10)
    publish: bool = False


class CreateRunRequest(BaseModel):
    task: str = Field(min_length=3, max_length=20_000)
    workspace: str = Field(default_factory=lambda: str(Path.cwd()))
    options: RunOptions = Field(default_factory=RunOptions)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    kind: str = Field(default="observation", min_length=1, max_length=50)
    run_id: str | None = None


class DelegationRequest(BaseModel):
    from_agent: str
    to_agent: str
    task: str = Field(min_length=1, max_length=20_000)
    context: dict = Field(default_factory=dict)


def require_run(run_id: str) -> dict:
    run = run_service.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run nicht gefunden")
    return run


@router.post("/runs", status_code=202)
def create_run(request: CreateRunRequest):
    try:
        return run_service.create(
            task=request.task,
            workspace=request.workspace,
            publish=request.options.publish,
            timeout_seconds=request.options.timeout_seconds,
            max_tool_calls=request.options.max_tool_calls,
            max_repair_attempts=request.options.max_repair_attempts,
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs")
def list_runs(limit: int = 50):
    return run_service.list_runs(max(1, min(limit, 200)))


@router.get("/config")
def get_runtime_config():
    return {
        "default_workspace": str(Path.cwd().resolve()),
        "model": MODEL,
        "defaults": {
            "timeout_seconds": 1200,
            "max_tool_calls": 50,
            "max_repair_attempts": 5,
        },
    }


@router.get("/agents")
def list_canonical_agents():
    active_run = next(
        (
            run
            for run in run_service.list_runs(200)
            if run["status"]
            not in {"completed", "failed", "cancelled"}
        ),
        None,
    )
    return agent_roster(active_run)


@router.get("/agent-statuses")
def list_agent_statuses():
    return [
        {"id": status, "description": description}
        for status, description in AGENT_STATUS_DEFINITIONS.items()
    ]


@router.get("/agents/{agent_id}")
def get_canonical_agent(agent_id: str):
    agent = get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden")
    return agent


@router.get("/agents/{agent_id}/memory")
def get_agent_memory(agent_id: str, run_id: str | None = None, limit: int = 100):
    try:
        return agent_team.memory(agent_id, run_id=run_id, limit=max(1, min(limit, 500)))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/agents/{agent_id}/memory", status_code=201)
def add_agent_memory(agent_id: str, request: MemoryRequest):
    try:
        return agent_team.remember(
            agent_id,
            request.content,
            kind=request.kind,
            run_id=request.run_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    return require_run(run_id)


@router.get("/runs/{run_id}/agents")
def get_run_agents(run_id: str):
    return agent_roster(require_run(run_id))


@router.get("/runs/{run_id}/diff")
def get_run_diff(run_id: str):
    try:
        return change_service.preview(require_run(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/runs/{run_id}/apply")
def apply_run_changes(run_id: str):
    run = require_run(run_id)
    try:
        result = change_service.apply(run)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run_service.add_event(run_id, "changes.applied", result)
    return result


@router.get("/runs/{run_id}/delegations")
def get_run_delegations(run_id: str):
    require_run(run_id)
    return agent_team.delegations(run_id)


@router.post("/runs/{run_id}/delegations", status_code=201)
def create_delegation(run_id: str, request: DelegationRequest):
    require_run(run_id)
    try:
        delegation = agent_team.delegate(
            run_id,
            request.from_agent,
            request.to_agent,
            request.task,
            context=request.context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    run_service.add_event(run_id, "agent.delegated", delegation)
    return delegation


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str):
    run = run_service.cancel(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run nicht gefunden")
    return run


@router.post("/runs/{run_id}/resume")
def resume_run(run_id: str):
    try:
        run = run_service.resume(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="Run nicht gefunden")
    return run


@router.get("/runs/{run_id}/events")
def get_events(run_id: str, after: int = 0):
    require_run(run_id)
    return run_service.events(run_id, max(after, 0))


@router.get("/runs/{run_id}/report")
def get_report(run_id: str):
    report = run_service.report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Run nicht gefunden")
    return Response(
        report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="run-{run_id}.md"'},
    )


@router.get("/runs/{run_id}/files/content")
def get_run_file(run_id: str, path: str):
    run = require_run(run_id)
    try:
        file = resolve_workspace_path(run["workspace"], path, must_exist=True)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not file.is_file():
        raise HTTPException(status_code=400, detail="Kein Dateiobjekt")
    return {
        "path": file.relative_to(Path(run["workspace"])).as_posix(),
        "content": file.read_text(encoding="utf-8", errors="ignore"),
    }


@router.websocket("/ws/runs/{run_id}")
async def run_events_socket(websocket: WebSocket, run_id: str):
    if run_service.get(run_id) is None:
        await websocket.close(code=4404, reason="Run nicht gefunden")
        return
    await websocket.accept()
    last_id = 0
    try:
        while True:
            events = run_service.events(run_id, last_id)
            for event in events:
                await websocket.send_json(event)
                last_id = event["id"]
            run = run_service.get(run_id)
            if run and run["status"] in {"completed", "failed", "cancelled"}:
                await websocket.send_json({"type": "run.snapshot", "payload": run})
                await websocket.close(code=1000)
                return
            await asyncio.sleep(0.5)
    except (WebSocketDisconnect, RuntimeError):
        return
