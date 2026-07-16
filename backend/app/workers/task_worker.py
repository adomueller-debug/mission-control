import traceback

from backend.app.database.database import SessionLocal
from backend.app.models.task import Task
from backend.app.providers.factory import provider


def process_task(task_id: str):
    print(f"[Worker] Start: {task_id}")

    db = SessionLocal()

    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if task is None:
            print("[Worker] Task not found")
            return

        task.status = "running"
        db.commit()

        print("[Worker] Calling provider...")

        answer = provider.generate(task.instruction)

        print("[Worker] Provider response:")
        print(answer)

        task.result = answer
        task.status = "completed"
        db.commit()

        print("[Worker] Task completed")

    except Exception:
        error = traceback.format_exc()
        print(error)

        if "task" in locals() and task is not None:
            task.status = "failed"
            task.result = error
            db.commit()

    finally:
        db.close()
