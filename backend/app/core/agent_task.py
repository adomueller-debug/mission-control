from dataclasses import dataclass, field


@dataclass
class AgentTask:
    id: str
    instruction: str
    assigned_agent: str
    status: str = "pending"

    tool: str | None = None
    result: str | None = None
    metadata: dict = field(default_factory=dict)
