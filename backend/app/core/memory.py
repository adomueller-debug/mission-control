from collections import defaultdict


class MemoryManager:
    def __init__(self):
        self._memory = defaultdict(list)

    def add(self, agent_id: str, item: str):
        self._memory[agent_id].append(item)

    def get(self, agent_id: str) -> list[str]:
        return self._memory[agent_id]

    def clear(self, agent_id: str):
        self._memory[agent_id].clear()


memory = MemoryManager()
