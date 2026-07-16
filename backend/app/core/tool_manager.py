from backend.app.tools.registry import get_tool
from backend.app.core.tool_result import ToolResult


class ToolManager:
    def execute(self, tool_name: str, *args):
        try:
            tool = get_tool(tool_name)
            result = tool.run(*args)
            return ToolResult(True, str(result))
        except Exception as e:
            return ToolResult(False, str(e))


tool_manager = ToolManager()
