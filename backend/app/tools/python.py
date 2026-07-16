import subprocess
import tempfile
from pathlib import Path


def execute(code: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "script.py"
        file.write_text(code, encoding="utf-8")

        result = subprocess.run(
            ["python3", str(file)],
            capture_output=True,
            text=True,
        )

        return result.stdout if result.returncode == 0 else result.stderr
