from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from apps.mission_control.core.prompts import build_system_prompt
from apps.mission_control.core.ollama import chat

system_prompt = build_system_prompt("boss")

antwort = chat(
    system_prompt=system_prompt,
    user_prompt="Stelle dich in einem Satz vor."
)

print(antwort)
