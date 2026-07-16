from pathlib import Path

AGENTS_DIR = Path("agents")


def get_agents():
    if not AGENTS_DIR.exists():
        return []

    return sorted(
        directory.name
        for directory in AGENTS_DIR.iterdir()
        if directory.is_dir()
    )
