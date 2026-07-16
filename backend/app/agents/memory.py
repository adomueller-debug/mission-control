import json
import os


class AgentMemory:
    def __init__(self, path="memory.json"):
        self.path = path
        self.store = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.store, f)

    def get(self, agent_id: str):
        return self.store.get(agent_id, [])

    def add(self, agent_id: str, entry: str):
        if agent_id not in self.store:
            self.store[agent_id] = []

        self.store[agent_id].append(entry)
        self._save()
