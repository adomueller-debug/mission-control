from pathlib import Path

from apps.mission_control.core.agent import load_agent
from apps.mission_control.core.context import build_project_context
from apps.mission_control.core.project import get_project_context


def build_system_prompt(agent_name: str, task: str) -> str:
    agent = load_agent(agent_name)

    if not agent:
        return ""

    prompt_path = Path("agents") / agent_name / "prompts" / "system.md"

    system_prompt = ""
    if prompt_path.exists():
        system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    project_context = get_project_context(task)

    return f"""
# Projekt

{build_project_context()}

# Relevante Projektdateien

{project_context}

# Agent

Name: {agent["name"]}
Rolle: {agent["role"]}
Status: {agent["status"]}

Mission:
{agent["mission"]}

# System Prompt

{system_prompt}
""".strip()
