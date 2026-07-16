from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.tools.base import Tool

ROOT = Path.cwd()


class ReadFileTool(Tool):
    name = "read_file"
    description = "Liest den Inhalt einer Textdatei aus dem Projekt."

    def run(self, **kwargs: Any) -> dict[str, str]:
        path_value = kwargs.get("path")

        if not isinstance(path_value, str) or not path_value:
            raise ValueError("Parameter 'path' fehlt.")

        file = (ROOT / path_value).resolve()

        if ROOT.resolve() not in file.parents:
            raise PermissionError("Dateipfad liegt außerhalb des Projekts.")

        if not file.exists() or not file.is_file():
            raise FileNotFoundError(path_value)

        return {
            "path": path_value,
            "content": file.read_text(
                encoding="utf-8",
                errors="ignore",
            ),
        }


read_file_tool = ReadFileTool()
