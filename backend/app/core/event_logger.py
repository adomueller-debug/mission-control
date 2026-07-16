from backend.app.core.agent_events import AgentEvent


class EventLogger:
    def __init__(self):
        self.events = []

    def log(self, agent: str, action: str, payload: dict):
        self.events.append(
            AgentEvent(
                agent=agent,
                action=action,
                payload=payload,
            )
        )

    def all(self):
        return self.events


event_logger = EventLogger()
