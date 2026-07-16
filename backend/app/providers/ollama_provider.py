import ollama
import time

from backend.app.providers.base import BaseProvider


class OllamaProvider(BaseProvider):

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:

        start = time.time()
        print("[Ollama] Request started")

        if system_prompt:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        else:
            messages = [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]

        response = ollama.chat(
            model="qwen2.5:7b",
            messages=messages,
        )

        duration = time.time() - start
        print(f"[Ollama] Done in {duration:.2f}s")

        return response["message"]["content"]
