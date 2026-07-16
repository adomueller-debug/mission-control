from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.workspace_security import resolve_workspace_path

ROOT = Path.cwd()

_pending: dict[str, dict[str, str]] = {}


def create_patch(path: str, content: str) -> dict[str, str]:
    file = resolve_workspace_path(ROOT, path)

    if file.exists() and not file.is_file():
        raise ValueError("Kein Dateiobjekt")

    old_content = (
        file.read_text(encoding="utf-8")
        if file.exists()
        else ""
    )

    patch_id = f"patch-{uuid4().hex[:12]}"

    _pending[patch_id] = {
        "path": path,
        "old_content": old_content,
        "new_content": content,
    }

    return {
        "patch_id": patch_id,
        "path": path,
        "old_content": old_content,
        "new_content": content,
    }


def get_pending() -> dict[str, dict[str, str]]:
    return _pending
