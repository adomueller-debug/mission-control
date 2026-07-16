from typing import Type

from backend.app.agents.base import BaseAgent
from backend.app.agents.planner_agent import PlannerAgent
from backend.app.agents.coder_agent import CoderAgent
from backend.app.agents.analyst_agent import AnalystAgent


class AgentFactory:
    _agents: dict[str, Type[BaseAgent]] = {
        "planner": PlannerAgent,
        "coder": CoderAgent,
        "analyst": AnalystAgent,
    }

    @classmethod
    def create(cls, name: str) -> BaseAgent:
        agent_cls = cls._agents.get(name)

        if agent_cls is None:
            raise ValueError(f"Unknown agent: {name}")

        return agent_cls()
