from backend.app.agents.base import BaseAgent
from backend.app.context.repository_context import repository_context
from backend.app.core.tool_result import ToolResult
from backend.app.providers.factory import provider


class CoderAgent(BaseAgent):
    name = "coder"

    def execute(self, context):
        current_step = context.variables.get("current_step")

        if current_step is None:
            plan = context.variables.get("plan")

            if isinstance(plan, dict):
                actions = plan.get("actions", [])
                if actions:
                    current_step = actions[0]

        tool_result = context.variables.get("tool_result")

        tool_output = ""
        if isinstance(tool_result, ToolResult):
            tool_output = tool_result.output

        repository = repository_context.build(context.instruction)

        step_description = ""
        if current_step is not None:
            step_description = getattr(current_step, "description", str(current_step))

        prompt = f"""
Task:
{context.instruction}

Repository Context:
{repository}

Current Step:
{step_description}

Tool Output:
{tool_output}

Return ONLY the required code or patch.
"""

        return provider.generate(
            prompt=prompt,
            system_prompt="You are an expert software engineer.",
        )
