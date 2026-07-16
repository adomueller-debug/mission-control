from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class TaskResult:
    success: bool
    output: str
    created_at: str = datetime.now(UTC).isoformat()
