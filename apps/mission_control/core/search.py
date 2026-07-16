from pathlib import Path

EXCLUDED = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "data",
    "backups",
}


def find_relevant_files(query: str, limit: int = 10):
    words = {
        word.lower()
        for word in query.split()
        if len(word) > 2
    }

    matches = []

    for path in Path(".").rglob("*"):
        if not path.is_file():
            continue

        if any(part in EXCLUDED for part in path.parts):
            continue

        if path.suffix not in {
            ".py",
            ".md",
            ".yaml",
            ".yml",
            ".txt",
        }:
            continue

        score = 0

        path_str = str(path).lower()

        for word in words:
            if word in path_str:
                score += 5

        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()

            for word in words:
                if word in content:
                    score += 1

        except Exception:
            continue

        if score > 0:
            matches.append((score, path))

    matches.sort(key=lambda x: x[0], reverse=True)

    return [str(path) for score, path in matches[:limit]]
