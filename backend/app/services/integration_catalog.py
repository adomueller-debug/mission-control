from __future__ import annotations

import os
import urllib.request
from typing import Any

from backend.app.services.github_auth import github_auth_status


INTEGRATIONS: list[dict[str, Any]] = [
    {
        "id": "ollama",
        "name": "Ollama",
        "category": "ai",
        "description": "Lokale Modelle für Planung und Agentenentscheidungen.",
        "owner_agent": "sage",
        "account_required": False,
        "cost": "Kostenlos und lokal",
        "secret_groups": [],
        "configurable_keys": [],
        "setup_steps": [
            "Ollama lokal installieren und starten.",
            "Das konfigurierte Modell herunterladen.",
            "OLLAMA_URL nur bei abweichender Adresse setzen.",
        ],
    },
    {
        "id": "github",
        "name": "GitHub",
        "category": "development",
        "description": "Repositories, Pull Requests, Checks und Auto-Merge.",
        "owner_agent": "mercury",
        "account_required": True,
        "cost": "Kostenloser Account ausreichend",
        "secret_groups": [["GH_TOKEN", "GITHUB_TOKEN", "Git Credential Helper"]],
        "configurable_keys": ["GITHUB_TOKEN"],
        "setup_steps": [
            "Kostenlosen GitHub-Account verwenden.",
            "Bestehenden Git Credential Helper, GitHub CLI oder GITHUB_TOKEN verwenden.",
            "Repository-Zugriff und Branch-Regeln prüfen.",
        ],
    },
    {
        "id": "smtp",
        "name": "Gmail Drafts",
        "category": "communication",
        "description": "Freigabepflichtige E-Mail-Entwürfe über Google OAuth; kein automatischer Versand.",
        "owner_agent": "flow",
        "account_required": True,
        "cost": "Anbieterabhängig; oft kleines Freikontingent",
        "secret_groups": [["N8N_GMAIL_CREDENTIAL_ID", "SMTP_PASSWORD"]],
        "configurable_keys": ["N8N_GMAIL_CREDENTIAL_ID", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"],
        "setup_steps": [
            "Gmail API im lokalen Google-Cloud-Projekt aktivieren.",
            "Gmail OAuth2 in n8n verbinden und die Credential-ID hinterlegen.",
            "Workflows auf Entwurfserstellung begrenzen; Versand bleibt gesperrt.",
        ],
    },
    {
        "id": "n8n",
        "name": "n8n",
        "category": "automation",
        "description": "Optionale Ausführung wiederkehrender API-, Webhook- und Zeitplan-Workflows.",
        "owner_agent": "flow",
        "account_required": False,
        "cost": "Selbst gehostet ohne Lizenzkosten für den MVP",
        "secret_groups": [["N8N_BASE_URL"], ["N8N_API_KEY"]],
        "configurable_keys": ["N8N_BASE_URL", "N8N_API_KEY"],
        "setup_steps": [
            "n8n erst für einen konkreten wiederkehrenden Workflow einrichten.",
            "Lokal per Docker starten und N8N_BASE_URL setzen.",
            "In den lokalen n8n-Einstellungen einen API-Key erzeugen und als N8N_API_KEY hinterlegen.",
        ],
    },
    {
        "id": "google_workspace",
        "name": "Google Drive & Sheets CRM",
        "category": "crm",
        "description": "Projektablage, Lead-CRM, Aktivitäten und AURA-Designreferenzen.",
        "owner_agent": "flow",
        "account_required": True,
        "cost": "Kostenlos im vorhandenen Google-Konto",
        "secret_groups": [
            ["GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID"],
            ["GOOGLE_SHEETS_CRM_SPREADSHEET_ID"],
            ["N8N_GOOGLE_SHEETS_CREDENTIAL_ID"],
        ],
        "configurable_keys": [
            "GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID",
            "GOOGLE_SHEETS_CRM_SPREADSHEET_ID",
            "N8N_GOOGLE_SHEETS_CREDENTIAL_ID",
        ],
        "setup_steps": [
            "Google Drive und das CRM-Sheet im gewünschten Konto anlegen.",
            "Google-Sheets-OAuth in n8n verbinden.",
            "Die n8n-Credential-ID lokal konfigurieren und den Verbindungstest ausführen.",
        ],
    },
    {
        "id": "paypal",
        "name": "PayPal",
        "category": "finance",
        "description": "Zahlungslinks, Rechnungsstatus und Zahlungseingänge über PayPal.",
        "owner_agent": "orbit",
        "account_required": True,
        "cost": "Sandbox kostenlos; Live-Zahlungen mit Transaktionskosten",
        "secret_groups": [["PAYPAL_CLIENT_ID"], ["PAYPAL_CLIENT_SECRET"]],
        "configurable_keys": ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_ENVIRONMENT"],
        "setup_steps": [
            "PayPal Developer App zunächst im Sandbox-Modus erstellen.",
            "PAYPAL_CLIENT_ID und PAYPAL_CLIENT_SECRET lokal konfigurieren.",
            "Erst nach Tests und rechtlicher Prüfung auf Live umstellen.",
        ],
    },
]

INTEGRATION_BY_ID = {item["id"]: item for item in INTEGRATIONS}


def integration_status(integration: dict[str, Any]) -> dict[str, Any]:
    groups: list[list[str]] = integration["secret_groups"]
    secrets = []
    complete = True
    for alternatives in groups:
        present_name = next((name for name in alternatives if os.getenv(name)), None)
        secrets.append(
            {
                "names": alternatives,
                "configured": present_name is not None,
                "configured_name": present_name,
            }
        )
        complete = complete and present_name is not None

    detected = False
    if integration["id"] == "github":
        detected = bool(github_auth_status()["configured"])
        if detected and secrets:
            secrets[0] = {
                "names": groups[0],
                "configured": True,
                "configured_name": "Git Credential Helper",
            }
    elif integration["id"] == "ollama":
        url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
        tags_url = url.rsplit("/api/", 1)[0] + "/api/tags"
        try:
            with urllib.request.urlopen(tags_url, timeout=1) as response:
                detected = response.status == 200
        except Exception:
            detected = False

    ready = detected or (complete and bool(groups))
    return {
        **integration,
        "status": "ready" if ready else "missing",
        "ready": ready,
        "detected": detected,
        "secrets": secrets,
    }


def integration_catalog() -> list[dict[str, Any]]:
    return [integration_status(item) for item in INTEGRATIONS]
