from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from apps.mission_control.core.prompts import build_system_prompt

print(build_system_prompt("boss"))
