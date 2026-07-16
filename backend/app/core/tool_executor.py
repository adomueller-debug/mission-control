from __future__ import annotations

from typing import Any

from backend.app.tools.registry import get_tool, list_tools


class ToolExecutor:
    def list_tools(self) -> list[str]:
        return list_tools()

    def execute(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Any:
        tool = get_tool(tool_name)
        return tool.run(**kwargs)


tool_executor = ToolExecutor()
