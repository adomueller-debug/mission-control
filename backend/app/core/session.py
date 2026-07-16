from dataclasses import dataclass, field


@dataclass
class Session:
    task_id: str
    agent_id: str

    history: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
