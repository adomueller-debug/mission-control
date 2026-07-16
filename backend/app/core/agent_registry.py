from backend.app.agents.registry import registry


class AgentRegistryFacade:
    def get(self, name: str):
        return registry.get(name)

    def all(self):
        return registry._agents


agent_registry = AgentRegistryFacade()
