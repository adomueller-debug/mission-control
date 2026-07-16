import json

from backend.app.agents.coordinator import coordinate
from backend.app.core.memory import memory
from backend.app.database.database import SessionLocal
from backend.app.models.task import Task


def run_task(task_id: str):
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        task.status = "running"
        db.commit()

        result = coordinate(task)

        memory.add(task.agent_id, str(result))

        task.result = json.dumps(result, ensure_ascii=False, default=str)
        task.status = "completed"

        db.commit()

    except Exception as e:
        if task:
            task.status = "failed"
            task.result = str(e)
            db.commit()

    finally:
        db.close()
