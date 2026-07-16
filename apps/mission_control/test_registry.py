from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from apps.mission_control.registry.registry import AgentRegistry

registry = AgentRegistry()

agent = registry.register("boss")

print("Name :", agent.name)
print("Modell:", agent.model)
