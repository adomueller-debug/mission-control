from apps.mission_control.core.tasks import run_task


def delegate(agent: str, task: str):
    print(f"\n➡️ Delegiere an {agent.upper()}...")
    result = run_task(agent, task)

    return {
        "agent": agent,
        "task": task,
        "status": "completed",
        "result": result,
    }
