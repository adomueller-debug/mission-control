from __future__ import annotations

import json

from backend.app.services.llm_planner import LLMPlanner


class MockLLMPlanner(LLMPlanner):
    def next_tool_call(
        self,
        task: str,
        history: list[dict],
        tools: list[str],
    ) -> str:
        if not history:
            return json.dumps(
                {
                    "tool": "search_symbols",
                    "arguments": {
                        "query": "WorkflowService",
                    },
                }
            )

        return json.dumps(
            {
                "tool": "finish",
                "arguments": {},
            }
        )


mock_llm_planner = MockLLMPlanner()
