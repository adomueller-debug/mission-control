from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from apps.mission_control.core.settings import load_config
from apps.mission_control.core.cli import parse_args
from apps.mission_control.core.agents import get_agents
from apps.mission_control.core.agent import load_agent


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

        if agent:
            role = agent.get("role", "-")
            print(f"• {name} ({role})")
        else:
            print(f"• {name}")


def main():
    args = parse_args()
    config = load_config()

    if args.command == "status":
        show_status(config)
    elif args.command == "start":
        print(f"{config['app']['name']} wird gestartet...")


if __name__ == "__main__":
    main()
