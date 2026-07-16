from collections import defaultdict


class AgentMetrics:
    def __init__(self):
        self.metrics = defaultdict(int)

    def increment(self, agent: str):
        self.metrics[agent] += 1

    def all(self):
        return dict(self.metrics)


agent_metrics = AgentMetrics()
