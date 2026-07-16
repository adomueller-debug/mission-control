from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv, set_key

from build_n8n_business_workflow import main as build_business_workflow


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
WORKFLOW = ROOT / "n8n/workflows/mission-control-business-automation.json"
WORKFLOW_ENV_KEYS = (
    "N8N_BUSINESS_AUTOMATION_WORKFLOW_ID",
    "N8N_WEBSITE_SALES_WORKFLOW_ID",
    "N8N_SALES_LEAD_WORKFLOW_ID",
    "N8N_PROJECT_DELIVERY_WORKFLOW_ID",
)
LEGACY_WORKFLOW_NAMES = {
    "Mission Control – Website Sales Heidelberg",
    "Mission Control – CRM Lead & Gmail Draft",
    "Mission Control – Project Delivery Sync",
}


def _payload(path: Path) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    replacements = {
        "__GOOGLE_DRIVE_CREDENTIAL_ID__": os.getenv(
            "N8N_GOOGLE_DRIVE_CREDENTIAL_ID", ""
        ),
        "__GOOGLE_SHEETS_CREDENTIAL_ID__": os.getenv(
            "N8N_GOOGLE_SHEETS_CREDENTIAL_ID", ""
        ),
        "__GMAIL_CREDENTIAL_ID__": os.getenv("N8N_GMAIL_CREDENTIAL_ID", ""),
    }
    serialized = json.dumps(source)
    for placeholder, value in replacements.items():
        serialized = serialized.replace(placeholder, value)
    source = json.loads(serialized)
    return {
        key: source[key]
        for key in ("name", "nodes", "connections", "settings")
        if key in source
    }


def sync() -> None:
    load_dotenv(ENV_FILE, override=True)
    build_business_workflow()
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
    required = (
        "N8N_GOOGLE_DRIVE_CREDENTIAL_ID",
        "N8N_GOOGLE_SHEETS_CREDENTIAL_ID",
        "N8N_GMAIL_CREDENTIAL_ID",
    )
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Fehlende n8n-Credentials: {', '.join(missing)}")

    # Webhook paths must be unique among active workflows, so retire the three
    # previous partial workflows before activating the consolidated workflow.
    for name in LEGACY_WORKFLOW_NAMES:
        workflow = existing.get(name)
        if workflow and workflow.get("active"):
            deactivated = requests.post(
                f"{base}/api/v1/workflows/{workflow['id']}/deactivate",
                headers=headers,
                timeout=30,
            )
            deactivated.raise_for_status()

    payload = _payload(WORKFLOW)
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
    for env_key in WORKFLOW_ENV_KEYS:
        set_key(str(ENV_FILE), env_key, workflow_id, quote_mode="always")

    for name in LEGACY_WORKFLOW_NAMES:
        legacy = existing.get(name)
        if not legacy:
            continue
        deleted = requests.delete(
            f"{base}/api/v1/workflows/{legacy['id']}",
            headers=headers,
            timeout=30,
        )
        deleted.raise_for_status()
    print(f"{payload['name']}: aktiv ({workflow_id}); Legacy-Workflows entfernt")


if __name__ == "__main__":
    sync()
