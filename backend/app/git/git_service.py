import subprocess
from dataclasses import dataclass


@dataclass
class GitStatus:
    success: bool
    output: str


class GitService:

    def diff(self):
        return subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
        ).stdout

    def status(self):
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
        )

        return GitStatus(
            success=result.returncode == 0,
            output=result.stdout,
        )

    def commit(self, message: str):
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)


git_service = GitService()
