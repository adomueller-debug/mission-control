from backend.app.core.agent_capabilities import CAPABILITIES


class CapabilityManager:
    def get(self, agent: str):
        return CAPABILITIES[agent]


capabilities = CapabilityManager()
