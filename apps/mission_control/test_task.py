from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from apps.mission_control.core.tasks import run_task

antwort = run_task(
    "boss",
    "Plane die Entwicklung von Mission Control für die nächsten drei Schritte."
)

print(antwort)
