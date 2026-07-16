from pathlib import Path


class RepositoryMap:

    def build(self, root: str = "backend/app"):

        tree = []

        for path in sorted(Path(root).rglob("*")):

            if "__pycache__" in str(path):
                continue

            if path.is_dir():
                continue

            tree.append(
                {
                    "path": str(path),
                    "suffix": path.suffix,
                    "size": path.stat().st_size,
                }
            )

        return tree


repository_map = RepositoryMap()
