from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.mission_router import mission_router

router = APIRouter(prefix="/api/v1", tags=["Mission Router"])


class CreateMissionPlanRequest(BaseModel):
    goal: str | None = Field(default=None, min_length=3, max_length=20_000)


@router.get("/projects/{project_id}/mission-plans")
def list_mission_plans(project_id: str):
    return mission_router.project_plans(project_id)


@router.post("/projects/{project_id}/mission-plans", status_code=201)
def create_mission_plan(project_id: str, request: CreateMissionPlanRequest):
    try:
        return mission_router.create_plan(project_id, request.goal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden") from exc


@router.get("/mission-plans/{plan_id}")
def get_mission_plan(plan_id: str):
    plan = mission_router.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Missionsplan nicht gefunden")
    return plan


@router.post("/mission-plans/{plan_id}/approve")
def approve_mission_plan(plan_id: str):
    try:
        return mission_router.approve(plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Missionsplan nicht gefunden") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
