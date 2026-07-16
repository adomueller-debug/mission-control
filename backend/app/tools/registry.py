from __future__ import annotations

from typing import Dict

from backend.app.tools.base import Tool
from backend.app.tools.read_file import read_file_tool
from backend.app.tools.search_symbols import search_symbols_tool
from backend.app.tools.write_patch import write_patch_tool
from backend.app.tools.validate_project import validate_project_tool
from backend.app.tools.filesystem import filesystem


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list(self) -> list[str]:
        return sorted(self._tools.keys())


registry = ToolRegistry()
registry.register(read_file_tool)
registry.register(search_symbols_tool)
registry.register(write_patch_tool)
registry.register(validate_project_tool)
registry.register(filesystem)


# Rückwärtskompatible API
def register_tool(tool: Tool) -> None:
    registry.register(tool)



def get_tool(name: str) -> Tool:
    return registry.get(name)


def list_tools() -> list[str]:
    return registry.list()
