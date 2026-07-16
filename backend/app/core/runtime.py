from backend.app.core.agent_factory import AgentFactory


class Runtime:
    def run(self, agent_name: str, context):
        agent = AgentFactory.create(agent_name)
        return agent.execute(context)


runtime = Runtime()
