from backend.app.core.session import Session


class SessionManager:
    def __init__(self):
        self.sessions = {}

    def get(self, task_id: str, agent_id: str):
        if task_id not in self.sessions:
            self.sessions[task_id] = Session(
                task_id=task_id,
                agent_id=agent_id,
            )

        return self.sessions[task_id]


session_manager = SessionManager()
