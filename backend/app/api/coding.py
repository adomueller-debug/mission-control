from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.core.orchestrator import orchestrator


router = APIRouter(prefix="/coding", tags=["coding"])


class ImproveRequest(BaseModel):
    path: str


@router.post("/improve")
def improve_file(request: ImproveRequest):
    class Task:
        id = "manual"
        agent_id = "coder"
        instruction = f"improve: {request.path}"

    result = orchestrator.execute(Task())

    return {
        "success": getattr(result, "success", True),
        "result": result,
    }
