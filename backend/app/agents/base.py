from abc import ABC, abstractmethod
from backend.app.core.context import AgentContext


class BaseAgent(ABC):
    name = "base"

    @abstractmethod
    def execute(self, context: AgentContext):
        raise NotImplementedError
