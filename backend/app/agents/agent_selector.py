from backend.app.agents.router import build_prompt


def select_agent(instruction: str) -> str:
    text = instruction.lower()

    if any(k in text for k in ["plan", "planung"]):
        return "planner"

    if any(k in text for k in ["code", "build", "implement"]):
        return "coder"

    if any(k in text for k in ["analyse", "analyze", "why", "explain"]):
        return "analyst"

    return "general"


def build_agent_prompt(instruction: str) -> str:
    agent_type = select_agent(instruction)
    return build_prompt(agent_type, instruction)
