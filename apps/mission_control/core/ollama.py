import requests

from apps.mission_control.core.settings import load_config


def chat(system_prompt: str, user_prompt: str) -> str:
    config = load_config()

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": config["llm"]["default"],
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    return response.json()["message"]["content"]
