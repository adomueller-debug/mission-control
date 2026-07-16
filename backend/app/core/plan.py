from dataclasses import dataclass, field


@dataclass
class PlanStep:
    id: str
    description: str
    agent: str
    tool: str | None = None
    status: str = "pending"


@dataclass
class ExecutionPlan:
    task: str
    steps: list[PlanStep] = field(default_factory=list)
