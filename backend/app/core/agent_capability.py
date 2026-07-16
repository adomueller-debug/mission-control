from dataclasses import dataclass


@dataclass
class AgentCapability:
    name: str
    description: str
    tools: list[str]
