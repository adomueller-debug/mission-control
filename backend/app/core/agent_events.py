from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class AgentEvent:
    agent: str
    action: str
    payload: dict

    created_at: str = datetime.now(UTC).isoformat()
