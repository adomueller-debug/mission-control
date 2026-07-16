from backend.app.core.agent_state import AgentState


class AgentStateManager:
    def __init__(self):
        self.states = {}

    def get(self, name: str):
        if name not in self.states:
            self.states[name] = AgentState(name=name)

        return self.states[name]


agent_states = AgentStateManager()
