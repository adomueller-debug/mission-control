from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class RuntimeResult:
    success: bool
    output: object

    metadata: dict = field(default_factory=dict)

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
