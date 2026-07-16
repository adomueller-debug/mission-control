from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path.cwd()

SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
}


@dataclass(slots=True)
class IndexedFile:
    path: str
    extension: str
    size: int


def build_index() -> list[IndexedFile]:
    index: list[IndexedFile] = []

    for file in ROOT.rglob("*"):
        if (
            not file.is_file()
            or file.suffix.lower() not in SOURCE_EXTENSIONS
            or ".git" in file.parts
            or "node_modules" in file.parts
            or ".venv" in file.parts
        ):
            continue

        relative = file.relative_to(ROOT)

        index.append(
            IndexedFile(
                path=relative.as_posix(),
                extension=file.suffix.lower(),
                size=file.stat().st_size,
            )
        )

    return sorted(index, key=lambda f: f.path)
