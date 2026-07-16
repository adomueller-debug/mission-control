from pathlib import Path
import yaml


def load_agent(name: str):
    config_path = Path("agents") / name / "config.yaml"

    if not config_path.exists():
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def print_agent(agent: dict):
    print(f"\n{agent['name']}")
    print("-" * 50)

    print(f"Rolle : {agent['role']}")
    print(f"Status: {agent['status']}")

    print("\nMission")
    print(agent["mission"])

    print("\nPersönlichkeit")
    for item in agent.get("personality", []):
        print(f"• {item}")

    print("\nVerantwortlichkeiten")
    for item in agent.get("responsibilities", []):
        print(f"• {item}")

    print("\nDelegiert an")
    for item in agent.get("delegates", []):
        print(f"• {item}")
