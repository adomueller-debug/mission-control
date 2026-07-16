from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.services.planner import create_execution_plan
from backend.app.services.orchestrator import next_agent

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator"])


class WorkflowRequest(BaseModel):
    task: str


@router.post("/start")
def start_workflow(request: WorkflowRequest):
    plan = create_execution_plan(request.task)

    return {
        "plan": plan,
        "next_agent": next_agent(plan),
    }
