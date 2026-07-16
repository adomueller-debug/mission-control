class ResourceManager:
    def __init__(self):
        self.resources = {}

    def register(self, name, value):
        self.resources[name] = value

    def get(self, name):
        return self.resources.get(name)


resource_manager = ResourceManager()
