from dataclasses import dataclass, field


@dataclass
class TaskContext:
    task_id: str
    instruction: str

    variables: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
