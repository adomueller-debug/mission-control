from backend.app.agents.agent_selector import select_agent
from backend.app.agents.memory_sync import build_final_prompt


def route_agent(task):
    agent_type = select_agent(task.instruction)
    prompt = build_final_prompt(task.agent_id, task.instruction)
    return agent_type, prompt
