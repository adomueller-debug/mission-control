from __future__ import annotations

import asyncio
from datetime import datetime
import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.database import SessionLocal, get_db
from backend.app.models.mission_v2 import AgentAssignment, Approval, AuditedToolCall, QualityGate
from backend.app.models.project import ProjectArtifact
from backend.app.services.mission_v2_service import mission_v2_service
from backend.app.services.mission_planner_v2 import build_mission_dag
from backend.app.services.mission_scheduler_v2 import mission_scheduler_v2


router = APIRouter(prefix="/api/v2", tags=["Mission Control V2"])


class WorkItemInput(BaseModel):
    key: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    title: str = Field(min_length=2, max_length=300)
    description: str = Field(default="", max_length=20_000)
    agent_id: str = Field(min_length=2, max_length=50)
    priority: int = Field(default=3, ge=1, le=5)
    risk_level: int = Field(default=0, ge=0, le=3)
    dependencies: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    resource_keys: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    max_attempts: int = Field(default=3, ge=1, le=10)


class CreateMissionRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=20_000)
    project_id: str | None = None
    deadline: datetime | None = None
    budget_cents: int = Field(default=0, ge=0)
    autonomy_level: int = Field(default=1, ge=0, le=3)
    risk_level: int = Field(default=0, ge=0, le=3)
    success_criteria: list[str] = Field(default_factory=list, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)
    work_items: list[WorkItemInput] = Field(default_factory=list, max_length=200)


class ReplanMissionRequest(BaseModel):
    work_items: list[WorkItemInput] = Field(min_length=1, max_length=200)


class WorkItemStatusRequest(BaseModel):
    status: Literal[
        "queued", "ready", "active", "review", "retrying", "completed", "skipped", "blocked"
    ]
    skip_reason: str = Field(default="", max_length=2_000)

    @model_validator(mode="after")
    def require_skip_reason(self):
        if self.status == "skipped" and not self.skip_reason.strip():
            raise ValueError("skip_reason ist für übersprungene Work Items erforderlich")
        return self


class CreateApprovalRequest(BaseModel):
    mission_id: str
    work_item_id: str | None = None
    tool_call_id: str | None = None
    action_type: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=2, max_length=2_000)
    target: str = Field(default="", max_length=2_000)
    risk_level: int = Field(default=2, ge=2, le=3)
    payload_preview: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    note: str = Field(default="", max_length=2_000)


class CreateQualityGateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    work_item_id: str | None = None
    gate_type: str = Field(default="acceptance", max_length=50)
    required: bool = True


@router.post("/missions", status_code=201)
def create_mission(request: CreateMissionRequest, db: Session = Depends(get_db)):
    try:
        payload = request.model_dump()
        auto_plan = not payload["work_items"]
        if auto_plan:
            payload["work_items"] = build_mission_dag(payload["goal"])
        mission = mission_v2_service.create_mission(db, payload)
        if auto_plan:
            mission_scheduler_v2.start(mission["id"])
        return mission
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/missions")
def list_missions(
    status: str | None = Query(default=None), db: Session = Depends(get_db)
):
    try:
        return mission_v2_service.list_missions(db, status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str, db: Session = Depends(get_db)):
    mission = mission_v2_service.get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission nicht gefunden")
    return mission


@router.post("/missions/{mission_id}/cancel")
def cancel_mission(mission_id: str, db: Session = Depends(get_db)):
    try:
        return mission_v2_service.cancel(db, mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/resume")
def resume_mission(mission_id: str, db: Session = Depends(get_db)):
    try:
        mission = mission_v2_service.resume(db, mission_id)
        mission_scheduler_v2.start(mission_id)
        return mission
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/missions/{mission_id}/replan")
def replan_mission(
    mission_id: str, request: ReplanMissionRequest, db: Session = Depends(get_db)
):
    try:
        mission = mission_v2_service.replace_plan(
            db, mission_id, [item.model_dump() for item in request.work_items]
        )
        mission_scheduler_v2.start(mission_id)
        return mission
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/work-items/{work_item_id}/status")
def update_work_item_status(
    work_item_id: str,
    request: WorkItemStatusRequest,
    db: Session = Depends(get_db),
):
    try:
        return mission_v2_service.set_work_item_status(
            db, work_item_id, request.status, skip_reason=request.skip_reason
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/missions/{mission_id}/assignments")
def list_assignments(mission_id: str, db: Session = Depends(get_db)):
    if mission_v2_service.get_mission(db, mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission nicht gefunden")
    items = db.scalars(
        select(AgentAssignment)
        .where(AgentAssignment.mission_id == mission_id)
        .order_by(AgentAssignment.created_at)
    )
    return [mission_v2_service._assignment(item) for item in items]


def _timeline(db: Session, mission_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for assignment in db.scalars(select(AgentAssignment).where(AgentAssignment.mission_id == mission_id)):
        events.append({"id": f"assignment:{assignment.id}", "type": "assignment.status", "created_at": assignment.started_at or assignment.created_at, "payload": mission_v2_service._assignment(assignment)})
    for tool_call in db.scalars(select(AuditedToolCall).where(AuditedToolCall.mission_id == mission_id)):
        events.append({"id": f"tool:{tool_call.id}", "type": "tool.status", "created_at": tool_call.completed_at or tool_call.created_at, "payload": mission_v2_service._tool_call(tool_call)})
    for gate in db.scalars(select(QualityGate).where(QualityGate.mission_id == mission_id)):
        events.append({"id": f"gate:{gate.id}", "type": "quality_gate.status", "created_at": gate.checked_at or gate.created_at, "payload": mission_v2_service._gate(gate)})
    for approval in db.scalars(select(Approval).where(Approval.mission_id == mission_id)):
        events.append({"id": f"approval:{approval.id}", "type": "approval.status", "created_at": approval.decided_at or approval.created_at, "payload": mission_v2_service._approval(approval)})
    return sorted(events, key=lambda event: event["created_at"])


@router.get("/missions/{mission_id}/events")
def list_mission_events(mission_id: str, db: Session = Depends(get_db)):
    if mission_v2_service.get_mission(db, mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission nicht gefunden")
    return _timeline(db, mission_id)


@router.websocket("/ws/missions/{mission_id}")
async def mission_event_stream(websocket: WebSocket, mission_id: str):
    await websocket.accept()
    last_payload = ""
    try:
        while True:
            with SessionLocal() as db:
                mission = mission_v2_service.get_mission(db, mission_id)
                if mission is None:
                    await websocket.close(code=4404)
                    return
                payload = json.dumps(
                    {"mission": mission, "events": _timeline(db, mission_id)},
                    ensure_ascii=False,
                    default=str,
                    sort_keys=True,
                )
            if payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.get("/missions/{mission_id}/artifacts")
def list_mission_artifacts(mission_id: str, db: Session = Depends(get_db)):
    mission = mission_v2_service.get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission nicht gefunden")
    if not mission["project_id"]:
        return []
    artifacts = db.scalars(
        select(ProjectArtifact)
        .where(ProjectArtifact.project_id == mission["project_id"])
        .order_by(ProjectArtifact.created_at.desc())
    )
    return [
        {
            "id": item.id,
            "project_id": item.project_id,
            "name": item.name,
            "artifact_type": item.artifact_type,
            "media_type": item.media_type,
            "size_bytes": item.size_bytes,
            "sync_status": item.sync_status,
            "external_url": item.external_url,
            "created_at": item.created_at,
        }
        for item in artifacts
    ]


@router.post("/missions/{mission_id}/quality-gates", status_code=201)
def create_quality_gate(
    mission_id: str,
    request: CreateQualityGateRequest,
    db: Session = Depends(get_db),
):
    try:
        return mission_v2_service.add_quality_gate(
            db, {"mission_id": mission_id, **request.model_dump()}
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@router.get("/approvals")
def list_approvals(
    status: str | None = Query(default="pending"), db: Session = Depends(get_db)
):
    return mission_v2_service.list_approvals(db, status)


@router.post("/approvals", status_code=201)
def create_approval(request: CreateApprovalRequest, db: Session = Depends(get_db)):
    try:
        return mission_v2_service.create_approval(db, request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/approve")
def approve(
    approval_id: str,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        return mission_v2_service.decide_approval(db, approval_id, True, request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/reject")
def reject(
    approval_id: str,
    request: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        return mission_v2_service.decide_approval(db, approval_id, False, request.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/agents")
def list_v2_agents(db: Session = Depends(get_db)):
    return mission_v2_service.agent_statuses(db)


@router.get("/budgets")
def get_budgets(
    mission_id: str | None = Query(default=None), db: Session = Depends(get_db)
):
    try:
        return mission_v2_service.budget_summary(db, mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
