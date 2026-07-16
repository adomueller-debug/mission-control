from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    task_id: str
    agent_id: str
    instruction: str

    plan = None

    memory: list[str] = field(default_factory=list)
    variables: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
