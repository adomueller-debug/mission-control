from __future__ import annotations

from pathlib import Path


class WorkspaceViolation(ValueError):
    """Raised when a requested path escapes its configured workspace."""


def resolve_workspace(value: str | Path | None = None) -> Path:
    root = Path(value or Path.cwd()).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise WorkspaceViolation(f"Workspace existiert nicht: {root}")
    return root


def resolve_workspace_path(
    workspace: str | Path,
    value: str | Path,
    *,
    must_exist: bool = False,
) -> Path:
    root = resolve_workspace(workspace)
    requested = Path(value)

    if requested.is_absolute():
        candidate = requested.resolve(strict=False)
    else:
        candidate = (root / requested).resolve(strict=False)

    if candidate != root and root not in candidate.parents:
        raise WorkspaceViolation("Dateipfad liegt außerhalb des Workspace.")

    if must_exist and not candidate.exists():
        raise FileNotFoundError(str(value))

    return candidate


def relative_workspace_path(workspace: str | Path, value: str | Path) -> str:
    root = resolve_workspace(workspace)
    return resolve_workspace_path(root, value).relative_to(root).as_posix()
