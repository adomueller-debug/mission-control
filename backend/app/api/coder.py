from fastapi import APIRouter

from backend.app.models.execution_plan import ExecutionPlan
from backend.app.services.coder import execute_plan

router = APIRouter(prefix="/coder", tags=["Coder"])


@router.post("/execute")
def execute(plan: ExecutionPlan):
    return execute_plan(plan)
