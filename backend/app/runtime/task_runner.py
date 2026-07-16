from backend.app.workers.multi_agent_runner import run_task


def run_worker_loop():
    import time
    from backend.app.database.database import SessionLocal
    from backend.app.models.task import Task

    print("[Runner] Started")

    while True:
        db = SessionLocal()

        try:
            task = db.query(Task).filter(Task.status == "queued").first()

            if not task:
                db.close()
                time.sleep(1)
                continue

            run_task(task.id)

        except Exception as e:
            print("[Runner ERROR]", e)

        finally:
            db.close()

        time.sleep(1)
