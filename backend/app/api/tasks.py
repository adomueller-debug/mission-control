from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.database.database import SessionLocal
from backend.app.models.task import Task
from backend.app.runtime.task_router import route_task

router = APIRouter()


class TaskRequest(BaseModel):
    agent_id: str
    instruction: str


@router.post("/tasks/")
def create_task(req: TaskRequest):
    db = SessionLocal()

    try:
        agent_type, prompt = route_task(req)

        task = Task(agent_id=req.agent_id, instruction=req.instruction, status="queued")

        db.add(task)
        db.commit()
        db.refresh(task)

        return {"id": task.id, "agent_type": agent_type, "status": task.status}

    finally:
        db.close()


@router.get("/tasks/")
def list_tasks():
    db = SessionLocal()
    try:
        return db.query(Task).all()
    finally:
        db.close()
