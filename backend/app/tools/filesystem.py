from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from backend.app.core.workspace_security import resolve_workspace_path
from backend.app.tools.base import Tool


class FileSystemTool(Tool):
    name = "filesystem"
    description = "Liest und verändert Dateien innerhalb des Workspace."

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or Path.cwd()).resolve()

    def _path(self, path: str, *, must_exist: bool = False) -> Path:
        return resolve_workspace_path(self.root, path, must_exist=must_exist)

    def read(self, path: str) -> str:
        return self._path(path, must_exist=True).read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> dict[str, str]:
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"status": "success", "file": target.relative_to(self.root).as_posix()}

    def edit(self, **kwargs: Any):
        target = kwargs.get("path") or kwargs.get("file")
        content = kwargs.get("content") or kwargs.get("code")
        if not isinstance(target, str):
            raise ValueError("Missing path.")
        if not isinstance(content, str):
            raise ValueError("Missing content.")
        return self.write(target, content)

    def exists(self, path: str) -> bool:
        return self._path(path).exists()

    def mkdir(self, path: str) -> None:
        self._path(path).mkdir(parents=True, exist_ok=True)

    def copy(self, source: str, destination: str) -> dict[str, str]:
        src = self._path(source, must_exist=True)
        dst = self._path(destination)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return {"status": "success"}

    def run(self, **kwargs: Any) -> Any:
        operation = kwargs.pop("operation", "read")
        method = getattr(self, operation, None)
        if method is None or operation.startswith("_"):
            raise ValueError(f"Unbekannte Dateisystem-Operation: {operation}")
        return method(**kwargs)


filesystem = FileSystemTool()
