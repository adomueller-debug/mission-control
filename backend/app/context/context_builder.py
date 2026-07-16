from pathlib import Path

from backend.app.planning.file_selector import file_selector


class ContextBuilder:

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
                }
            )

        return context


context_builder = ContextBuilder()
