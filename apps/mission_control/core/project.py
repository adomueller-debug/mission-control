from pathlib import Path

from apps.mission_control.core.search import find_relevant_files


def get_project_context(query: str, limit: int = 5) -> str:
    parts = []

    for filename in find_relevant_files(query, limit):
        path = Path(filename)

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        parts.append(f"# Datei: {filename}\n")
        parts.append(content[:4000])
        parts.append("\n")

    return "\n".join(parts)
