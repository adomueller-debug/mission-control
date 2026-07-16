from __future__ import annotations

from backend.app.core.tool_executor import tool_executor
from backend.app.services.tool_planner import tool_planner


class ToolAgent:

    def plan(self, task: str):
        return tool_planner.plan(task)

    def available_tools(self) -> list[str]:
        return tool_executor.list_tools()

    def search_symbol(self, query: str):
        return tool_executor.execute(
            "search_symbols",
            query=query,
        )

    def read_file(self, path: str):
        return tool_executor.execute(
            "read_file",
            path=path,
        )


tool_agent = ToolAgent()
