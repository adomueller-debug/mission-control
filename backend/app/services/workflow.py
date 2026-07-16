from backend.app.models.execution_plan import ExecutionPlan
from backend.app.services.coder import execute_plan


def execute_workflow(plan: ExecutionPlan):
    coder_result = execute_plan(plan)

    if coder_result["status"] != "completed":
        return coder_result

    patches = []

    for file in coder_result["files"]:
        patches.append(
            {
                "path": file["path"],
                "content": file["content"],
            }
        )

    return {
        "status": "completed",
        "summary": coder_result["summary"],
        "patches": patches,
    }
