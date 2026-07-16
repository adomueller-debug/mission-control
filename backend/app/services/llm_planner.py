from __future__ import annotations

from abc import ABC, abstractmethod


class LLMPlanner(ABC):
    @abstractmethod
    def next_tool_call(
        self,
        task: str,
        history: list[dict],
        tools: list[str],
    ) -> str:
        """Liefert einen Tool-Call als JSON-String."""
        raise NotImplementedError
