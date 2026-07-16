from pathlib import Path

from backend.app.core.workspace_security import resolve_workspace_path

MAX_FILE_CONTEXT = 3_500
MAX_TOTAL_CONTEXT = 18_000


def load_workspace_context(files: list[str], workspace: str | Path | None = None) -> str:
    root = Path(workspace or Path.cwd()).resolve()
    sections: list[str] = []

    for relative_path in files:
        path = resolve_workspace_path(root, relative_path)

        if not path.exists() or not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if len(content) > MAX_FILE_CONTEXT:
            content = content[:MAX_FILE_CONTEXT] + "\n...<truncated>..."

        section = f"### FILE: {relative_path}\n\n{content}\n"
        if sum(len(item) for item in sections) + len(section) > MAX_TOTAL_CONTEXT:
            break
        sections.append(section)

    return "\n".join(sections)
