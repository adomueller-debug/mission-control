from backend.app.workers.multi_agent_runner import run_task


def dispatch(task_id: str):
    run_task(task_id)
