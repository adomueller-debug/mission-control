import re

from backend.app.services.file_selector import select_relevant_files

from backend.app.models.execution_plan import (
    ExecutionPlan,
    PlanStep,
)


def create_execution_plan(task: str, workspace: str | None = None) -> ExecutionPlan:
    creation_mode = bool(
        re.search(
            r"(?:website|landingpage|prototyp).{0,80}(?:bauen|erstellen|implementieren)"
            r"|(?:bauen|erstellen|implementieren).{0,80}(?:website|landingpage|prototyp)",
            task,
            re.IGNORECASE | re.DOTALL,
        )
    )
    project_match = re.search(r"^Projekt:\s*(.+)$", task, re.MULTILINE)
    project_name = project_match.group(1).strip() if project_match else "new-product"
    slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")
    output_directory = f"projects/{slug or 'new-product'}" if creation_mode else None
    relevant_files = (
        [] if creation_mode else select_relevant_files(task, workspace=workspace, limit=5)
    )

    return ExecutionPlan(
        goal=task,
        summary="Automatisch erzeugter Ausführungsplan",
        expected_files=relevant_files,
        creation_mode=creation_mode,
        output_directory=output_directory,
        steps=[
            PlanStep(
                id=1,
                title="Mission koordinieren",
                description="Ziel priorisieren und an FORGE delegieren",
                agent="boss",
            ),
            PlanStep(
                id=2,
                title="Technische Analyse",
                description="Repository und Änderungsumfang analysieren",
                agent="forge_planner",
            ),
            PlanStep(
                id=3,
                title="Implementierung",
                description="Code erzeugen",
                agent="forge_builder",
            ),
            PlanStep(
                id=4,
                title="Produktvalidierung",
                description="Code und Produkt gegen messbare Quality Gates prüfen",
                agent="forge_reviewer",
            ),
            PlanStep(
                id=5,
                title="Release Candidate",
                description="Releasebericht und reproduzierbaren Übergabestand erzeugen",
                agent="forge_publisher",
            ),
        ],
    )
