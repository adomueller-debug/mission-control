from pydantic import BaseModel


class PlanStep(BaseModel):
    id: int
    title: str
    description: str
    agent: str
    status: str = "pending"


class ExecutionPlan(BaseModel):
    goal: str
    summary: str
    steps: list[PlanStep]
    expected_files: list[str] = []
    creation_mode: bool = False
    output_directory: str | None = None
