from apps.mission_control.core.prompts import build_system_prompt
from apps.mission_control.core.ollama import chat
from apps.mission_control.core.tools import execute_tool


def run_task(agent_name: str, task: str) -> str:
    if task == "list agents":
        agents = execute_tool("list_agents")
        return "\n".join(agents)

    system_prompt = build_system_prompt(
        agent_name=agent_name,
        task=task,
    )

    return chat(
        system_prompt=system_prompt,
        user_prompt=task,
    )
