from dataclasses import dataclass


@dataclass
class AgentProfile:
    name: str
    system_prompt: str
    temperature: float = 0.2
    max_iterations: int = 5
