from dataclasses import dataclass, field


@dataclass
class RuntimeContext:
    task_id: str
    agent: str

    variables: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
