from __future__ import annotations

from backend.app.core.tool_executor import tool_executor
from backend.app.services.planner_factory import get_planner
from backend.app.services.tool_call_parser import parse_tool_call


class AgentLoopV2:
    def run(self, task: str):
        history: list[dict] = []

        while True:
            response = get_planner().next_tool_call(
                task=task,
                history=history,
                tools=tool_executor.list_tools(),
            )

            call = parse_tool_call(response)

            if call is None:
                raise RuntimeError("LLM lieferte kein gültiges Tool-JSON.")

            if call["tool"] == "finish":
                return history

            result = tool_executor.execute(
                call["tool"],
                **call["arguments"],
            )

            history.append(
                {
                    "tool": call["tool"],
                    "arguments": call["arguments"],
                    "result": result,
                }
            )

            if call["tool"] == "validate_project":
                if isinstance(result, dict) and not result.get("success", False):
                    history.append(
                        {
                            "type": "error",
                            "message": "Validation fehlgeschlagen. Repariere den Fehler.",
                            "details": result,
                        }
                    )


agent_loop_v2 = AgentLoopV2()
