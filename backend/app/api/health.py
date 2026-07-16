from __future__ import annotations

import json
import os
import subprocess
import urllib.request

from fastapi import APIRouter
from sqlalchemy import text

from backend.app.core.version import MISSION_CONTROL_VERSION
from backend.app.database.database import engine

router = APIRouter(prefix="/api/v1", tags=["Health"])


def _ollama_status() -> dict:
    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    tags_url = url.rsplit("/api/", 1)[0] + "/api/tags"
    try:
        with urllib.request.urlopen(tags_url, timeout=1) as response:
            payload = json.loads(response.read().decode())
        return {"ok": True, "models": len(payload.get("models", []))}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


@router.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = {"ok": True}
    except Exception as exc:
        database = {"ok": False, "error": type(exc).__name__}

    git = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, timeout=2
    )
    services = {
        "database": database,
        "git": {"ok": git.returncode == 0, "version": git.stdout.strip()},
        "ollama": _ollama_status(),
    }
    return {
        "version": MISSION_CONTROL_VERSION,
        "status": "ok" if all(service["ok"] for service in services.values()) else "degraded",
        "services": services,
    }
