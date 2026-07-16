from __future__ import annotations

from backend.app.services.tool_agent import tool_agent
from backend.app.services.reflection import reflection_engine


class AgentLoop:
    def run(self, task: str):
        results = []

        for call in tool_agent.plan(task):
            result = tool_agent.search_symbol(
                call.arguments["query"]
            )

            results.append(
                {
                    "tool": call.tool,
                    "arguments": call.arguments,
                    "result": result,
                }
            )

            if result:
                file_result = tool_agent.read_file(
                    result[0]["file"]
                )

                results.append(
                    {
                        "tool": "read_file",
                        "arguments": {
                            "path": result[0]["file"]
                        },
                        "result": {
                            "path": file_result["path"],
                            "characters": len(file_result["content"])
                        }
                    }
                )

        return {
            "steps": results,
            "reflection": reflection_engine.reflect(results),
        }


agent_loop = AgentLoop()
