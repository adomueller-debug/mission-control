from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    content: str
    created_at: str = datetime.now(UTC).isoformat()
