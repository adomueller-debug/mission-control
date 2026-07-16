from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv, set_key


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
WORKFLOWS = (
    (
        ROOT / "n8n/workflows/website-sales-heidelberg.json",
        "N8N_WEBSITE_SALES_WORKFLOW_ID",
    ),
    (
        ROOT / "n8n/workflows/website-sales-lead-processing.json",
        "N8N_SALES_LEAD_WORKFLOW_ID",
    ),
)


def _payload(path: Path) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    return {
        key: source[key]
        for key in ("name", "nodes", "connections", "settings")
        if key in source
    }


def sync() -> None:
    load_dotenv(ENV_FILE, override=True)
    base = os.environ["N8N_BASE_URL"].rstrip("/")
    headers = {
        "X-N8N-API-KEY": os.environ["N8N_API_KEY"],
        "Content-Type": "application/json",
    }
    response = requests.get(
        f"{base}/api/v1/workflows",
        params={"limit": 100},
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    existing = {item["name"]: item for item in response.json().get("data", [])}

    for path, env_key in WORKFLOWS:
        payload = _payload(path)
        workflow = existing.get(payload["name"])
        if workflow:
            workflow_id = workflow["id"]
            saved = requests.put(
                f"{base}/api/v1/workflows/{workflow_id}",
                headers=headers,
                json=payload,
                timeout=30,
            )
        else:
            saved = requests.post(
                f"{base}/api/v1/workflows",
                headers=headers,
                json=payload,
                timeout=30,
            )
        if not saved.ok:
            raise RuntimeError(
                f"n8n workflow update failed for {payload['name']} "
                f"({saved.status_code}): {saved.text[:1_000]}"
            )
        workflow_id = str(saved.json()["id"])
        activated = requests.post(
            f"{base}/api/v1/workflows/{workflow_id}/activate",
            headers=headers,
            timeout=30,
        )
        activated.raise_for_status()
        set_key(str(ENV_FILE), env_key, workflow_id, quote_mode="always")
        print(f"{payload['name']}: aktiv ({workflow_id})")


if __name__ == "__main__":
    sync()
