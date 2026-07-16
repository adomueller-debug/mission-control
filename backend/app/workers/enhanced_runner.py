from backend.app.database.database import SessionLocal
from backend.app.models.task import Task
from backend.app.agents.memory_store import memory


def run_task(task_id: str):
    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        print(f"[Runner] Processing {task.id}")

        task.status = "running"
        db.commit()

        from backend.app.agents.dispatcher import execute

        result = execute(task)

        memory.add(task.agent_id, f"in:{task.instruction} out:{result}")

        task.result = result
        task.status = "completed"

        db.commit()

        print("[Runner] Done")

    except Exception as e:
        if task:
            task.status = "failed"
            task.result = str(e)
            db.commit()

    finally:
        db.close()
