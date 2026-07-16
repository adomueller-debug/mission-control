from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Event:
    name: str
    payload: dict
    timestamp: str = datetime.now(UTC).isoformat()
