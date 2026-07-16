from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

MAX_OUTPUT = 50_000


def resolve_executable(name: str) -> str:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    for candidate in (
        Path("/opt/homebrew/bin") / name,
        Path("/usr/local/bin") / name,
    ):
        if candidate.is_file():
            return str(candidate)
    return name


def run_command(
    command: list[str],
    *,
    cwd: str | Path | None = None,
    timeout: int = 300,
) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = result.stdout + result.stderr
    return result.returncode == 0, output[-MAX_OUTPUT:]


def validation_commands(workspace: str | Path | None = None) -> list[tuple[str, list[str]]]:
    root = Path(workspace or Path.cwd()).resolve()
    commands: list[tuple[str, list[str]]] = []
    python = root / ".venv" / "bin"
    if (root / "backend").exists():
        commands.extend(
            [
                ("pytest", [str(python / "pytest"), "-q"]),
                ("ruff", [str(python / "ruff"), "check", "backend"]),
                (
                    "mypy",
                    [str(python / "mypy"), "backend/app", "--explicit-package-bases"],
                ),
            ]
        )
    if (root / "apps" / "mission_control").exists():
        commands.extend(
            [
                (
                    "mission-control-compile",
                    [
                        str(python / "python"),
                        "-m",
                        "compileall",
                        "-q",
                        "apps/mission_control",
                    ],
                ),
                (
                    "mission-control-ruff",
                    [
                        str(python / "ruff"),
                        "check",
                        "apps/mission_control",
                    ],
                ),
            ]
        )

    if (root / "frontend" / "package.json").exists():
        npm = resolve_executable("npm")
        commands.extend(
            [
                ("frontend-lint", [npm, "run", "lint"]),
                ("frontend-build", [npm, "run", "build"]),
            ]
        )
    return commands


def validate_project(workspace: str | Path | None = None) -> dict:
    root = Path(workspace or Path.cwd()).resolve()
    checks = []
    for name, command in validation_commands(root):
        cwd = root / "frontend" if name.startswith("frontend-") else root
        failure_class: str | None
        try:
            ok, output = run_command(command, cwd=cwd)
        except (OSError, subprocess.TimeoutExpired) as exc:
            ok, output = False, str(exc)
            failure_class = "infrastructure"
        else:
            failure_class = "code" if not ok else None
        checks.append(
            {
                "name": name,
                "success": ok,
                "output": output,
                "failure_class": failure_class,
            }
        )
    return {"success": all(check["success"] for check in checks), "checks": checks}
