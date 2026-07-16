class PluginManager:
    def __init__(self):
        self.plugins = {}

    def register(self, plugin):
        self.plugins[plugin.name] = plugin

    def get(self, name):
        return self.plugins[name]

    def all(self):
        return self.plugins.values()


plugin_manager = PluginManager()
