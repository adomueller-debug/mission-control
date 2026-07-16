class ServiceContainer:
    def __init__(self):
        self.services = {}

    def register(self, name: str, service):
        self.services[name] = service

    def resolve(self, name: str):
        return self.services[name]


container = ServiceContainer()
