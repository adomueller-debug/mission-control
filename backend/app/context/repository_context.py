from pathlib import Path

from backend.app.planning.file_selector import file_selector
from backend.app.repository.repository_map import repository_map


class RepositoryContext:

    def build(self, instruction: str):

        files = file_selector.select(instruction)

        context = []

        for file in files:

            try:
                content = Path(file).read_text(encoding="utf-8")
            except Exception:
                continue

            context.append(
                {
                    "path": file,
                    "content": content,
                    "lines": len(content.splitlines()),
                }
            )

        return {
            "instruction": instruction,
            "repository": repository_map.build(),
            "files": context,
        }


repository_context = RepositoryContext()
