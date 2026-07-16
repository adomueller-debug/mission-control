import re
from pathlib import Path

from backend.app.services.query_normalizer import STOP_WORDS

ROOT = Path.cwd()

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "data",
    ".mypy_cache",
    ".pytest_cache",
}

PRIORITY_EXTENSIONS = {
    ".py": 10,
    ".tsx": 9,
    ".ts": 8,
    ".jsx": 7,
    ".js": 6,
    ".md": 2,
}

MAX_FILE_SIZE = 100_000


def select_relevant_files(
    task: str, limit: int = 6, workspace: str | None = None
) -> list[str]:
    root = Path(workspace).resolve() if workspace else ROOT
    words = {
        word
        for word in re.findall(r"[\wäöüß]+", task.lower())
        if len(word) >= 3 and word not in STOP_WORDS
    }
    requests_tests = bool(words & {"test", "tests", "testabdeckung", "automatisiert"})

    matches: list[tuple[int, str]] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue

        ext = path.suffix.lower()

        if ext not in PRIORITY_EXTENSIONS:
            continue

        score = PRIORITY_EXTENSIONS[ext]

        relative_text = relative.as_posix().lower()

        for word in words:
            if word in relative_text:
                score += 50

        if requests_tests and ("test" in relative.parts or "tests" in relative.parts):
            score += 35

        try:
            if path.stat().st_size <= MAX_FILE_SIZE:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).lower()

                for word in words:
                    if word in content:
                        score += 8

                if "root" in words and ('@app.get("/")' in content or "def root(" in content):
                    score += 1000
                if "health" in words and '@router.get("/health")' in content:
                    score += 1000
        except OSError:
            continue

        matches.append((score, relative.as_posix()))

    matches.sort(reverse=True)

    return [path for _, path in matches[:limit]]
