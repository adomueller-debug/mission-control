from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class LLMResponse:
    success: bool
    content: str
    tokens: int = 0
    model: str = ""
    duration: float = 0.0
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
