from dataclasses import dataclass, field


@dataclass
class AgentState:
    name: str

    status: str = "idle"

    current_task: str | None = None

    completed_tasks: int = 0

    metadata: dict = field(default_factory=dict)
