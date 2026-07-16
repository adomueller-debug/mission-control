def build_prompt(agent_type: str, instruction: str) -> str:

    base = "You are an AI agent."

    if agent_type == "planner":
        return (
            base
            + "\nYou are a planning agent. Think structured and step-by-step.\n\nTask:\n"
            + instruction
        )

    if agent_type == "coder":
        return (
            base
            + "\nYou are a coding agent. Focus on implementation and code quality.\n\nTask:\n"
            + instruction
        )

    if agent_type == "analyst":
        return (
            base
            + "\nYou are an analysis agent. Focus on logic and insights.\n\nTask:\n"
            + instruction
        )

    return base + "\n\nTask:\n" + instruction
