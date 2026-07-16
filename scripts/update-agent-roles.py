from pathlib import Path
import yaml

ROLES = {
    "boss": "CEO",
    "forge": "Lead Developer",
    "aura": "Creative Director",
}

for name, role in ROLES.items():
    config = Path("agents") / name / "config.yaml"

    if not config.exists():
        continue

    data = yaml.safe_load(config.read_text())

    data["role"] = role

    config.write_text(
        yaml.dump(data, sort_keys=False),
        encoding="utf-8",
    )

print("✅ Rollen aktualisiert")
