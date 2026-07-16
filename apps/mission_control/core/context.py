from apps.mission_control.core.agents import get_agents
from apps.mission_control.core.agent import load_agent


def build_project_context() -> str:
    lines = [
        "Projekt: Mission Control",
        "",
        "Vorhandene Komponenten:",
        "- Open WebUI",
        "- Ollama",
        "- PostgreSQL",
        "- Qdrant",
        "- n8n",
        "",
        "Vorhandene Agenten:",
    ]

    for name in get_agents():
        agent = load_agent(name)

        if agent:
            lines.append(f"- {agent['name']}: {agent['role']}")

    lines.extend([
        "",
        "Regeln:",
        "- Nutze ausschließlich die oben aufgeführten Agenten.",
        "- Erfinde keine weiteren Agenten.",
        "- Erfinde keine Projektbestandteile.",
        "- Wenn Informationen fehlen, sage ausdrücklich, dass sie fehlen.",
    ])

    return "\n".join(lines)
