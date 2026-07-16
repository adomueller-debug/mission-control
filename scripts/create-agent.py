#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path

parser = argparse.ArgumentParser(description="Erstellt einen neuen Agenten aus der Vorlage")
parser.add_argument("name", help="Name des Agenten")
args = parser.parse_args()

name = args.name.lower()

template = Path("templates/agent")
target = Path("agents") / name

if target.exists():
    print(f"❌ Agent '{name}' existiert bereits.")
    exit(1)

shutil.copytree(template, target)

for file in target.rglob("*"):
    if file.is_file():
        text = file.read_text(encoding="utf-8")
        text = text.replace("FORGE", name.upper())
        text = text.replace("forge", name)
        file.write_text(text, encoding="utf-8")

print(f"✅ Agent '{name}' erfolgreich erstellt.")
