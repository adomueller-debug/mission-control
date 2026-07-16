from backend.app.core.config import settings


class ModelManager:
    def planner(self):
        return settings.MODEL

    def coder(self):
        return settings.MODEL

    def analyst(self):
        return settings.MODEL


models = ModelManager()
