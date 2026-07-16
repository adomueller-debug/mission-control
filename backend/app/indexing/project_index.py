from pathlib import Path


class ProjectIndex:
    def __init__(self, root: str = "backend"):
        self.root = Path(root)

    def python_files(self) -> list[str]:
        return sorted(
            str(path)
            for path in self.root.rglob("*.py")
            if "__pycache__" not in str(path)
        )

    def search(self, query: str) -> list[str]:
        query = query.lower()

        matches = []

        for file in self.python_files():
            try:
                text = Path(file).read_text(encoding="utf-8")
            except Exception:
                continue

            if query in text.lower():
                matches.append(file)

        return matches


project_index = ProjectIndex()
