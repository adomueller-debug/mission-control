from collections import defaultdict


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)

    def subscribe(self, event: str, callback):
        self._listeners[event].append(callback)

    def publish(self, event: str, payload=None):
        for callback in self._listeners[event]:
            callback(payload)


event_bus = EventBus()
