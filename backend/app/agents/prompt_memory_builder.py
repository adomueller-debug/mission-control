from backend.app.agents.memory_store import memory


def build_prompt_with_memory(agent_id: str, base_prompt: str) -> str:
    history = memory.get(agent_id)

    if not history:
        return base_prompt

    recent = history[-5:]

    memory_text = "\n".join(recent)

    return f"""You are an AI agent.

Previous context:
{memory_text}

Current task:
{base_prompt}
"""
