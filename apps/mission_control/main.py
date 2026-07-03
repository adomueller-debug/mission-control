from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from apps.mission_control.core.settings import load_config
from apps.mission_control.core.cli import parse_args
from apps.mission_control.core.agents import get_agents
from apps.mission_control.core.agent import load_agent, print_agent
from apps.mission_control.core.tasks import run_task
from apps.mission_control.core.delegation import delegate


def show_status(config):
    print("\nSystemstatus")
    print("-" * 50)
    print(f"Anwendung : {config['app']['name']}")
    print(f"Version   : {config['app']['version']}")
    print(f"LLM       : {config['llm']['default']}")
    print(f"Memory    : {config['memory']['provider']}")
    print(f"Datenbank : {config['database']['provider']}")

    print("\nAgenten")
    print("-" * 50)

    for name in get_agents():
        agent = load_agent(name)
        role = agent.get("role", "-") if agent else "-"
        print(f"• {name} ({role})")


def show_agent(name):
    agent = load_agent(name)

    if not agent:
        print(f"Agent '{name}' wurde nicht gefunden.")
        return

    print_agent(agent)


def run_agent(agent, task):
    result = run_task(agent, task)
    print(result)


def demo_delegation():
    result = delegate(
        "forge",
        "Erstelle einen Plan für die Implementierung einer Projektübersicht."
    )

    print("\nErgebnis")
    print("-" * 50)
    print(result["result"])


def main():
    args = parse_args()
    config = load_config()

    if args.command == "status":
        show_status(config)

    elif args.command == "agent":
        show_agent(args.name)

    elif args.command == "run":
        run_agent(args.agent, args.task)

    elif args.command == "start":
        demo_delegation()


if __name__ == "__main__":
    main()
