from dataclasses import dataclass
from typing import Any


@dataclass
class Action:
    agent: str
    tool: str
    operation: str
    arguments: dict[str, Any]
