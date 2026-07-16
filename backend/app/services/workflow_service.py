from backend.app.services.planner import create_execution_plan
from backend.app.services.coder import execute_plan
from backend.app.services.validator import validate_project


class WorkflowService:
    def execute(self, task: str) -> dict:
        plan = create_execution_plan(task)

        coder_result = execute_plan(plan)

        if coder_result.get("status") != "completed":
            return coder_result

        validation = validate_project()

        return {
            "plan": plan.model_dump(),
            "coder": coder_result,
            "validation": validation,
        }
