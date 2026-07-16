from backend.app.core.plan import ExecutionPlan, PlanStep
from backend.app.core.tool_selector import tool_selector


class PlanBuilder:
    def build(self, task: str, steps: list[str]):
        plan = ExecutionPlan(task=task)

        for i, step in enumerate(steps):
            plan.steps.append(
                PlanStep(
                    id=f"step_{i}",
                    description=step,
                    agent="coder",
                    tool=tool_selector.select(step),
                )
            )

        return plan


plan_builder = PlanBuilder()
