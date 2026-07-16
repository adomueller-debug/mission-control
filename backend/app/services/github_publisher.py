from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import requests

from backend.app.services.github_auth import github_token


class PublishError(RuntimeError):
    pass


def _run(command: list[str], cwd: Path, timeout: int = 120) -> str:
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise PublishError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:32] or "task"


def _repository_slug(remote: str) -> str:
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", remote)
    if match is None:
        raise PublishError("Origin ist kein unterstütztes GitHub-Repository.")
    return match.group(1)


def _github_request(
    method: str,
    url: str,
    *,
    token: str,
    payload: dict,
) -> dict:
    response = requests.request(
        method,
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
        timeout=60,
    )
    if response.status_code >= 400:
        raise PublishError(f"GitHub API Fehler {response.status_code}: {response.text[:1000]}")
    return response.json()


class GitHubPublisher:
    def publish(
        self,
        *,
        workspace: str,
        run_id: str,
        task: str,
        paths: list[str],
        validation_summary: str,
    ) -> dict[str, str]:
        root = Path(workspace).resolve()
        token = github_token()
        if not token:
            raise PublishError("Kein GitHub API-Zugang ist konfiguriert.")
        base = os.getenv(
            "GITHUB_BASE_BRANCH", _run(["git", "branch", "--show-current"], root)
        )
        branch = f"agent/{run_id[:8]}-{_slug(task)}"
        status = _run(["git", "status", "--porcelain"], root)
        dirty = {line[3:].strip() for line in status.splitlines() if len(line) > 3}
        unexpected = dirty.difference(paths)
        if unexpected:
            raise PublishError(
                "Workspace enthält fremde Änderungen: " + ", ".join(sorted(unexpected))
            )

        _run(["git", "switch", "-c", branch], root)
        _run(["git", "add", "--", *paths], root)
        _run(["git", "commit", "-m", f"feat(agent): {_slug(task)}"], root)
        _run(["git", "push", "-u", "origin", branch], root, timeout=300)
        remote = _run(["git", "remote", "get-url", "origin"], root)
        repository = _repository_slug(remote)
        body = (
            f"Autonomer Mission-Control-Run `{run_id}`.\n\n"
            f"## Aufgabe\n{task}\n\n## Validierung\n{validation_summary}"
        )
        pull_request = _github_request(
            "POST",
            f"https://api.github.com/repos/{repository}/pulls",
            token=token,
            payload={
                "title": task[:120],
                "head": branch,
                "base": base,
                "body": body,
            },
        )
        pr_url = pull_request["html_url"]
        _github_request(
            "POST",
            "https://api.github.com/graphql",
            token=token,
            payload={
                "query": "mutation($id:ID!){enablePullRequestAutoMerge(input:{pullRequestId:$id,mergeMethod:SQUASH}){pullRequest{url}}}",
                "variables": {"id": pull_request["node_id"]},
            },
        )
        return {"branch": branch, "pr_url": pr_url}


github_publisher = GitHubPublisher()
