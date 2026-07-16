from __future__ import annotations

import ast

from backend.app.core.workspace_security import resolve_workspace_path


def _duplicate_statements(source: str) -> list[str]:
    tree = ast.parse(source)
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        seen: dict[str, int] = {}
        for statement in node.body:
            fingerprint = ast.dump(statement, include_attributes=False)
            if fingerprint in seen:
                issues.append(
                    f"Doppeltes Statement in {node.name} (Zeilen {seen[fingerprint]} und {statement.lineno})."
                )
            else:
                seen[fingerprint] = statement.lineno
    return issues


def review_changes(workspace: str, paths: list[str]) -> dict:
    issues: list[str] = []
    for relative in paths:
        target = resolve_workspace_path(workspace, relative, must_exist=True)
        if target.suffix != ".py":
            continue
        try:
            source = target.read_text(encoding="utf-8")
            issues.extend(
                f"{relative}: {issue}" for issue in _duplicate_statements(source)
            )
        except (SyntaxError, UnicodeDecodeError) as exc:
            issues.append(f"{relative}: {exc}")
    return {"approved": not issues, "issues": issues}
