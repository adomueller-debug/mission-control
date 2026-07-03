from apps.mission_control.core.agents import get_agents


TOOLS = {
    "list_agents": lambda: get_agents(),
}


def execute_tool(name: str):
    tool = TOOLS.get(name)

    if tool is None:
        raise ValueError(f"Unbekanntes Tool: {name}")

    return tool()
