from collections import defaultdict


class RuntimeStats:
    def __init__(self):
        self.stats = defaultdict(int)

    def increment(self, key: str):
        self.stats[key] += 1

    def all(self):
        return dict(self.stats)


runtime_stats = RuntimeStats()
