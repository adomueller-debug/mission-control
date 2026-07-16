import time
from backend.app.providers.factory import provider
from backend.app.core.llm_response import LLMResponse


class LLMManager:
    def generate(self, prompt: str, system_prompt: str = ""):
        start = time.perf_counter()

        result = provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )

        return LLMResponse(
            success=True,
            content=result,
            duration=time.perf_counter() - start,
        )


llm = LLMManager()
