from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.services.planner import create_execution_plan

router = APIRouter(prefix="/planner", tags=["Planner"])


class PlanRequest(BaseModel):
    task: str


@router.post("/plan")
def create_plan(request: PlanRequest):
    return create_execution_plan(request.task)
