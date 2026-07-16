import asyncio

from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    set_default_openai_client,
)

client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

set_default_openai_client(client)

agent = Agent(
    name="BOSS",
    instructions="Du bist der CEO von Mission Control.",
    model="qwen3:8b",
)


async def main():
    result = await Runner.run(
        agent,
        "Stelle dich in einem Satz vor."
    )

    print(result.final_output)


asyncio.run(main())
