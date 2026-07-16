from pathlib import Path

from backend.app.indexing.project_index import project_index
from backend.app.planning.file_selector import file_selector


class ProjectAnalysisService:

    def analyze(self, instruction: str) -> dict:
        relevant_files = file_selector.select(instruction)

        analysis = []

        for file in relevant_files:
            try:
                content = Path(file).read_text(encoding="utf-8")
            except Exception:
                continue

            analysis.append({
                "path": file,
                "lines": len(content.splitlines()),
                "size": len(content),
            })

        return {
            "instruction": instruction,
            "relevant_files": relevant_files,
            "analysis": analysis,
            "total_python_files": len(project_index.python_files()),
        }


project_analysis_service = ProjectAnalysisService()
