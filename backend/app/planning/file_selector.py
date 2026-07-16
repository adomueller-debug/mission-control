from backend.app.indexing.project_index import project_index
from backend.app.providers.factory import provider


class FileSelector:

    def select(self, task: str, limit: int = 5):
        files = project_index.python_files()

        prompt = f"""
You are selecting files for a software engineering task.

Task:
{task}

Candidate files:

{chr(10).join(files)}

Return ONLY a JSON array containing the {limit} most relevant files.

Example:

[
  "backend/app/tools/filesystem.py",
  "backend/app/core/orchestrator.py"
]
"""

        response = provider.generate(
            prompt=prompt,
            system_prompt="You are an expert software architect."
        )

        try:
            import json

            result = json.loads(response)

            return [
                file
                for file in result
                if file in files
            ]

        except Exception:
            return []


file_selector = FileSelector()
