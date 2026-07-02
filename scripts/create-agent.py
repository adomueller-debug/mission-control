#!/usr/bin/env python3

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("name")
args = parser.parse_args()

agent = args.name.lower()
base = Path("agents") / agent

(base / "prompts").mkdir(parents=True, exist_ok=True)
(base / "knowledge").mkdir(parents=True, exist_ok=True)

(base / "README.md").write_text(f"""# {agent.upper()}

## Rolle

TODO

## Status

🚧 In Entwicklung
""")

(base / "config.yaml").write_text(f"""name: {agent.upper()}

role: TODO

status: active
""")

(base / "prompts" / "system.md").write_text(f"# {agent.upper()} System Prompt\n")
(base / "knowledge" / "mission.md").write_text(f"# {agent.upper()} Mission\n")

print(f"✅ Agent '{agent}' erstellt.")
