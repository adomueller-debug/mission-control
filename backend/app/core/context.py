from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    task_id: str
    agent_id: str
    instruction: str

    memory: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
