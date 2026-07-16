from backend.app.agents.tool_layer import run_tool


def run_tool_step(instruction: str) -> str:
    return run_tool(f"echo {instruction}")
