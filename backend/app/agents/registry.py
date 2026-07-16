from backend.app.agents.planner_agent import PlannerAgent
from backend.app.agents.coder_agent import CoderAgent
from backend.app.agents.analyst_agent import AnalystAgent


class AgentRegistry:
    def __init__(self):
        self._agents = {
            "planner": PlannerAgent(),
            "coder": CoderAgent(),
            "analyst": AnalystAgent(),
        }

    def get(self, name: str):
        return self._agents[name]


registry = AgentRegistry()
