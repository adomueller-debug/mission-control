from collections import defaultdict


class KnowledgeBase:
    def __init__(self):
        self._knowledge = defaultdict(list)

    def add(self, topic: str, value: str):
        self._knowledge[topic].append(value)

    def search(self, topic: str):
        return self._knowledge.get(topic, [])


knowledge = KnowledgeBase()
