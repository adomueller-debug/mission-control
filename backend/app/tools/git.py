import subprocess


def execute(command: list[str]) -> str:
    result = subprocess.run(
        ["git", *command],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return result.stderr

    return result.stdout
