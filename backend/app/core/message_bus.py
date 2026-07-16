from collections import defaultdict


class MessageBus:
    def __init__(self):
        self.messages = defaultdict(list)

    def send(self, receiver, message):
        self.messages[receiver].append(message)

    def receive(self, receiver):
        data = self.messages[receiver]
        self.messages[receiver] = []
        return data


bus = MessageBus()
