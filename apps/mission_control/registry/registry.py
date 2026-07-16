from agents import Agent

from apps.mission_control.core.agent import load_agent
from apps.mission_control.core.settings import load_config


class AgentRegistry:
    def __init__(self):
        self._agents = {}
        self._config = load_config()

    def register(self, name: str):
        config = load_agent(name)

        if not config:
            raise ValueError(f"Agent '{name}' wurde nicht gefunden.")

        model = config.get(
            "model",
            self._config["llm"]["default"],
        )

        agent = Agent(
            name=config["name"],
            instructions=config["mission"],
            model=model,
        )

        self._agents[name] = agent
        return agent

    def get(self, name: str):
        return self._agents.get(name)
