from backend.app.agents.prompt_memory_builder import build_prompt_with_memory


def build_final_prompt(agent_id: str, instruction: str) -> str:
    base_prompt = instruction
    return build_prompt_with_memory(agent_id, base_prompt)
