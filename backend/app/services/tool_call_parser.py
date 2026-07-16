from __future__ import annotations

import json
import re


def parse_tool_call(text: str) -> dict | None:
    if not text:
        return None

    # Qwen Thinking entfernen
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL,
    )

    # Markdown JSON Block entfernen
    text = text.replace("```json", "")
    text = text.replace("```", "")

    # Erst versuchen direkt JSON zu lesen
    try:
        data = json.loads(text.strip())

        if isinstance(data, dict) and "tool" in data:
            return data

    except json.JSONDecodeError:
        pass

    # JSON Objekt aus Text extrahieren
    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL,
    )

    if not match:
        return None

    try:
        data = json.loads(match.group())

        if isinstance(data, dict) and "tool" in data:
            return data

    except json.JSONDecodeError:
        return None

    return None
