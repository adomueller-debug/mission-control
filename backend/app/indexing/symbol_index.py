from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path.cwd()

EXCLUDED_PARTS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "data",
    "dist",
    "node_modules",
}


@dataclass(slots=True)
class Symbol:
    name: str
    kind: str
    file: str
    line: int


def build_symbol_index() -> list[Symbol]:
    symbols: list[Symbol] = []

    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)

        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue

        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        relative_path = relative.as_posix()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        file=relative_path,
                        line=node.lineno,
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    Symbol(
                        name=node.name,
                        kind="function",
                        file=relative_path,
                        line=node.lineno,
                    )
                )

    return sorted(
        symbols,
        key=lambda symbol: (
            symbol.file,
            symbol.line,
            symbol.name,
        ),
    )
