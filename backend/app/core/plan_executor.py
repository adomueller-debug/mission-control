from backend.app.core.runtime import runtime
from backend.app.core.tool_router import tool_router


class PlanExecutor:
    def execute(self, context):
        results = []

        for step in context.plan.steps:
            context.variables["current_step"] = step

            if step.tool:
                tool_result = tool_router.execute(
                    "coder",
                    step.tool,
                    step.description,
                )
                context.variables["tool_result"] = tool_result

            result = runtime.run(step.agent, context)
            results.append(result)

        return results


plan_executor = PlanExecutor()
