from pathlib import Path
import yaml


def load_agent(name: str):
    config_path = Path("agents") / name / "config.yaml"

    if not config_path.exists():
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
