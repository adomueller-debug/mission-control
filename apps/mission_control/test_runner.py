import asyncio

from agents import Agent, Runner

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
