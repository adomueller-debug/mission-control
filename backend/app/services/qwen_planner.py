from __future__ import annotations

import json
import urllib.request

from backend.app.services.llm_planner import LLMPlanner
from backend.app.services.tool_schema import get_tool_schemas


class QwenPlanner(LLMPlanner):
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        url: str = "http://127.0.0.1:11434/api/generate",
    ):
        self.model = model
        self.url = url

    def next_tool_call(
        self,
        task: str,
        history: list[dict],
        tools: list[str],
    ) -> str:

        prompt = f"""
Du bist ein Coding-Agent.

Aufgabe:
{task}

Verfügbare Tools:
{json.dumps(get_tool_schemas(), indent=2)}

Bisherige Schritte:
{json.dumps(history, indent=2, ensure_ascii=False)}

Agent Regeln:

- Nutze read_file bevor du write_patch verwendest.
- Nach jedem write_patch muss validate_project ausgeführt werden.
- Wenn validate_project Fehler enthält:
  - analysiere die Fehlermeldung,
  - finde die betroffene Datei,
  - nutze read_file,
  - erstelle einen korrigierenden write_patch,
  - führe validate_project erneut aus.
- Beende erst mit finish, wenn validate_project erfolgreich war.
- Verwende nur existierende Tools.

Antworte ausschließlich mit gültigem JSON.

Format:

{{
  "tool": "tool_name",
  "arguments": {{}}
}}

Wenn keine weiteren Schritte notwendig sind:

{{
  "tool": "finish",
  "arguments": {{}}
}}
"""

        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode()

        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(request) as response:
            data = json.loads(
                response.read().decode()
            )

        return data["response"].strip()


qwen_planner = QwenPlanner()
