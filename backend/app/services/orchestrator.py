from backend.app.models.execution_plan import ExecutionPlan

def next_agent(plan: ExecutionPlan) -> str | None:
    for step in plan.steps:
        if step.status == "pending":
            return step.agent
    return None
