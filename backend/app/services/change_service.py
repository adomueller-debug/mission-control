from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


MAX_DIFF_BYTES = 1_000_000
SANDBOX_RUNTIME_PATHS = {".venv", "frontend/node_modules"}


def _git(
    arguments: list[str],
    cwd: Path,
    *,
    input_text: str | None = None,
) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = (process.stdout + process.stderr)[-MAX_DIFF_BYTES:]
    if process.returncode != 0:
        raise RuntimeError(output.strip() or f"git {' '.join(arguments)} fehlgeschlagen")
    return process.stdout


class ChangeService:
    def preview(self, run: dict[str, Any]) -> dict[str, Any]:
        if run["status"] != "completed":
            raise ValueError("Nur abgeschlossene Runs besitzen übernehmbare Änderungen.")
        sandbox = Path(run["workspace"]).resolve()
        source = Path(run["source_workspace"]).resolve()
        if sandbox == source:
            raise ValueError("Der Run besitzt keinen isolierten Änderungs-Workspace.")
        if not sandbox.is_dir() or not source.is_dir():
            raise ValueError("Run- oder Quell-Workspace ist nicht mehr verfügbar.")

        status = _git(["status", "--porcelain", "--untracked-files=all"], sandbox)
        untracked = [
            line[3:]
            for line in status.splitlines()
            if line.startswith("?? ")
            and line[3:].rstrip("/") not in SANDBOX_RUNTIME_PATHS
        ]
        patch = _git(["diff", "--binary", "--no-ext-diff", "HEAD", "--"], sandbox)
        files = [
            line
            for line in _git(["diff", "--name-only", "HEAD", "--"], sandbox).splitlines()
            if line
        ]
        return {
            "run_id": run["id"],
            "source_workspace": str(source),
            "files": files,
            "diff": patch,
            "untracked_files": untracked,
            "can_apply": bool(patch) and not untracked,
        }

    def apply(self, run: dict[str, Any]) -> dict[str, Any]:
        preview = self.preview(run)
        if preview["untracked_files"]:
            raise ValueError(
                "Neue, unversionierte Dateien können noch nicht lokal übernommen werden: "
                + ", ".join(preview["untracked_files"])
            )
        patch = preview["diff"]
        if not patch:
            raise ValueError("Der Run enthält keine Änderungen.")
        source = Path(preview["source_workspace"])
        source_status = _git(
            ["status", "--porcelain", "--untracked-files=all"], source
        )
        if source_status.strip():
            raise ValueError(
                "Der Quell-Workspace enthält lokale Änderungen. Bitte zuerst committen "
                "oder sichern, damit keine Arbeit vermischt wird."
            )
        _git(["apply", "--check", "--whitespace=error-all", "-"], source, input_text=patch)
        _git(["apply", "--index", "--whitespace=error-all", "-"], source, input_text=patch)
        try:
            _git(
                [
                    "-c",
                    "user.name=Mission Control",
                    "-c",
                    "user.email=mission-control@local",
                    "commit",
                    "-m",
                    f"chore: apply mission control run {run['id'][:8]}",
                ],
                source,
            )
        except RuntimeError:
            _git(["apply", "--reverse", "--index", "-"], source, input_text=patch)
            raise
        commit = _git(["rev-parse", "HEAD"], source).strip()
        return {
            "applied": True,
            "files": preview["files"],
            "source_workspace": str(source),
            "commit": commit,
        }


change_service = ChangeService()
