
import json

from backend.app.agents.base import BaseAgent
from backend.app.planning.file_selector import file_selector
from backend.app.providers.factory import provider


class PlannerAgent(BaseAgent):
    name = "planner"

    def execute(self, context):
        files = file_selector.select(context.instruction)

        prompt = f'''
You are an autonomous software engineer.

Task:
{context.instruction}

Relevant files:
{files}

Return ONLY valid JSON.

Example:

{{
  "actions":[
    {{
      "agent":"coder",
      "tool":"filesystem",
      "operation":"read",
      "arguments":{{
        "path":"backend/app/tools/filesystem.py"
      }}
    }}
  ]
}}
'''

        response = provider.generate(
            prompt=prompt,
            system_prompt="Return JSON only."
        )

        try:
            return json.loads(response)
        except Exception:
            return {"actions":[]}
