from pathlib import Path

EXCLUDED = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}


def list_project_files():
    files = []

    for path in Path(".").rglob("*"):
        if not path.is_file():
            continue

        if any(part in EXCLUDED for part in path.parts):
            continue

        files.append(str(path))

    return sorted(files)
