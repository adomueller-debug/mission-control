from dataclasses import dataclass


@dataclass
class ToolInvocation:
    tool: str
    arguments: dict
