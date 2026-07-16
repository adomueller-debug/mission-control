from collections import defaultdict


class TaskEventBus:
    def __init__(self):
        self.listeners = defaultdict(list)

    def subscribe(self, event: str, callback):
        self.listeners[event].append(callback)

    def publish(self, event: str, payload=None):
        for callback in self.listeners[event]:
            callback(payload)


task_event_bus = TaskEventBus()
