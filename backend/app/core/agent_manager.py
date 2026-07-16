from backend.app.core.runtime import runtime


class AgentManager:
    def run(self, agent_name: str, context):
        return runtime.run(agent_name, context)


agent_manager = AgentManager()
