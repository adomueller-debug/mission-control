from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class WorkspacePreparationError(RuntimeError):
    pass


def _git(command: list[str], cwd: Path, timeout: int = 120) -> str:
    result = subprocess.run(
        ["git", *command],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise WorkspacePreparationError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def _link_runtime_dependencies(source: Path, sandbox: Path) -> None:
    links = [
        (source / ".venv", sandbox / ".venv"),
        (source / "frontend" / "node_modules", sandbox / "frontend" / "node_modules"),
    ]
    for target, link in links:
        if target.exists() and not link.exists():
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target, target_is_directory=True)


def prepare_isolated_workspace(source: str, run_id: str) -> str:
    source_root = Path(source).resolve()
    sandbox = Path(tempfile.gettempdir()) / "mission-control-runs" / run_id
    if sandbox.exists():
        return str(sandbox.resolve())
    sandbox.parent.mkdir(parents=True, exist_ok=True)

    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=source_root,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if git_dir.returncode == 0:
        dirty = _git(["status", "--porcelain"], source_root)
        if dirty:
            raise WorkspacePreparationError(
                "Quell-Workspace enthält uncommittete Änderungen. Bitte zuerst sichern."
            )
        _git(["worktree", "add", "--detach", str(sandbox), "HEAD"], source_root, 300)
    else:
        shutil.copytree(
            source_root,
            sandbox,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "node_modules", "dist", "__pycache__"
            ),
        )
    _link_runtime_dependencies(source_root, sandbox)
    return str(sandbox.resolve())


def discard_isolated_workspace(source: str, run_id: str) -> None:
    sandbox_root = Path(tempfile.gettempdir()) / "mission-control-runs"
    sandbox = sandbox_root / run_id
    if not sandbox.exists() or sandbox.parent.resolve() != sandbox_root.resolve():
        return
    source_root = Path(source).resolve()
    removed = subprocess.run(
        ["git", "worktree", "remove", "--force", str(sandbox)],
        cwd=source_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if removed.returncode != 0 and sandbox.exists():
        shutil.rmtree(sandbox)
