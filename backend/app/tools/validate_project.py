from __future__ import annotations

from typing import Any

from backend.app.services.validator import validate_project
from backend.app.tools.base import Tool


class ValidateProjectTool(Tool):
    name = "validate_project"
    description = "Führt Projektvalidierung mit Ruff und MyPy aus."

    def run(self, **kwargs: Any) -> dict:
        return validate_project()


validate_project_tool = ValidateProjectTool()
