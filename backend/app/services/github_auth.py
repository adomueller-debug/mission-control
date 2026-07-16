from __future__ import annotations

import os
import subprocess

import requests


def github_token() -> str | None:
    """Return a GitHub token without persisting or logging credential-helper output."""
    configured = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    fields = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    return fields.get("password") or None


def github_auth_status(*, verify: bool = False) -> dict[str, object]:
    token = github_token()
    if not token:
        return {"configured": False, "verified": False, "login": None}
    if not verify:
        return {"configured": True, "verified": False, "login": None}
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
        )
        if response.status_code != 200:
            return {"configured": True, "verified": False, "login": None}
        return {
            "configured": True,
            "verified": True,
            "login": response.json().get("login"),
        }
    except requests.RequestException:
        return {"configured": True, "verified": False, "login": None}
