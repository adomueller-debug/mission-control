from __future__ import annotations

from dataclasses import dataclass
from backend.app.services.query_normalizer import normalize_query


@dataclass(slots=True)
class ToolCall:
    tool: str
    arguments: dict


class ToolPlanner:
    def plan(self, task: str) -> list[ToolCall]:
        task_lower = task.lower()

        calls: list[ToolCall] = []

        if any(word in task_lower for word in ("workflow", "service", "class", "funktion")):
            calls.append(
                ToolCall(
                    tool="search_symbols",
                    arguments={"query": normalize_query(task)},
                )
            )

        return calls


tool_planner = ToolPlanner()


TOOL_CALL_PROMPT = """
Du bist ein Tool-Planer.

Verfügbare Tools:
- search_symbols(query)
- read_file(path)
- write_patch(path, content)

Antworte ausschließlich als JSON.

Beispiel:

{
  "tool":"search_symbols",
  "arguments":{
      "query":"WorkflowService"
  }
}
"""
