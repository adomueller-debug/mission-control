from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Checkpoint:
    task_id: str
    state: dict
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
