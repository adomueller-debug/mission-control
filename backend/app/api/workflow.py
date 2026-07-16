from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["Workflow"])


class WorkflowRequest(BaseModel):
    task: str


service = WorkflowService()


@router.post("/execute")
def execute(request: WorkflowRequest):
    return service.execute(request.task)
