from collections import defaultdict


class AgentMemory:
    def __init__(self):
        self._memory = defaultdict(list)

    def add(self, agent: str, role: str, content: str):
        self._memory[agent].append(
            {
                "role": role,
                "content": content,
            }
        )

    def history(self, agent: str):
        return self._memory[agent]

    def clear(self, agent: str):
        self._memory[agent].clear()


agent_memory = AgentMemory()
