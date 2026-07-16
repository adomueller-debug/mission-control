from backend.app.agents.base import BaseAgent
from backend.app.providers.factory import provider


class AnalystAgent(BaseAgent):
    name = "analyst"

    def execute(self, context):
        prompt = f"""
Task:
{context.instruction}

Implementation:
{context.variables["implementation"]}

Review the implementation.
"""

        return provider.generate(
            prompt=prompt, system_prompt="You are a senior QA agent."
        )
