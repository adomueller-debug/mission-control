from backend.app.tools.filesystem import filesystem
from backend.app.tools.python import execute as python_execute
from backend.app.tools.shell import execute as shell_execute
from backend.app.providers.factory import provider


class CodingTool:

    def read(self, path: str):
        return filesystem.read(path)

    def write(self, path: str, content: str):
        filesystem.write(path, content)
        return "written"

    def improve(self, path: str):
        code = filesystem.read(path)

        prompt = f"""
You are a senior Python software engineer.

Improve the following file.

Rules:
- Keep behaviour identical.
- Improve readability.
- Add typing if useful.
- Do not explain anything.

Return ONLY the full new file.

{code}
"""

        improved = provider.generate(
            prompt=prompt,
            system_prompt="You are an expert Python engineer."
        )

        filesystem.write(path, improved)

        return path

    def run_checks(self):
        return {
            "ruff": shell_execute("ruff check backend"),
            "mypy": shell_execute("mypy backend/app --explicit-package-bases"),
        }

    def run_python(self, code: str):
        return python_execute(code)



    def improve_project(self, path: str):
        return self.improve(path)


coding = CodingTool()
