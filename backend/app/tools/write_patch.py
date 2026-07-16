from __future__ import annotations

from typing import Any

from backend.app.services.patch_service import create_patch
from backend.app.tools.base import Tool


class WritePatchTool(Tool):
    name = "write_patch"
    description = "Erzeugt einen Patch für eine Datei."

    def run(self, **kwargs: Any) -> dict[str, str]:
        path = kwargs.get("path")
        content = kwargs.get("content")

        if not isinstance(path, str) or not path:
            raise ValueError("Parameter 'path' fehlt.")

        if not isinstance(content, str):
            raise ValueError("Parameter 'content' fehlt.")

        patch = create_patch(
            path=path,
            content=content,
        )

        return {
            "patch_id": patch["patch_id"],
            "path": patch["path"],
        }


write_patch_tool = WritePatchTool()
