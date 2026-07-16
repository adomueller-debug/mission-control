from backend.app.core.capability_manager import capabilities
from backend.app.core.tool_manager import tool_manager


class ToolRouter:
    def execute(self, agent: str, tool: str, *args):
        capability = capabilities.get(agent)

        if tool not in capability.tools:
            raise PermissionError(f"{agent} cannot use tool '{tool}'")

        return tool_manager.execute(tool, *args)


tool_router = ToolRouter()
