from __future__ import annotations

import os

from backend.app.services.llm_planner import LLMPlanner
from backend.app.services.mock_llm_planner import mock_llm_planner
from backend.app.services.qwen_planner import qwen_planner


def get_planner() -> LLMPlanner:
    provider = os.getenv("AI_PLANNER", "mock").lower()

    match provider:
        case "mock":
            return mock_llm_planner

        case "qwen":
            return qwen_planner

        case _:
            raise RuntimeError(
                f"Unbekannter Planner: {provider}"
            )
