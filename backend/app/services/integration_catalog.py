from __future__ import annotations

import os
import shutil
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
            ["N8N_GOOGLE_DRIVE_CREDENTIAL_ID"],
        ],
        "configurable_keys": [
            "GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID",
            "GOOGLE_SHEETS_CRM_SPREADSHEET_ID",
            "N8N_GOOGLE_SHEETS_CREDENTIAL_ID",
            "N8N_GOOGLE_DRIVE_CREDENTIAL_ID",
            "N8N_PROJECT_DELIVERY_WEBHOOK_URL",
        ],
        "setup_steps": [
            "Google Drive und das CRM-Sheet im gewünschten Konto anlegen.",
            "Google Sheets und Google Drive OAuth in n8n verbinden.",
            "Beide n8n-Credential-IDs sowie den Delivery-Webhook lokal konfigurieren.",
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
    {
        "id": "google_calendar",
        "name": "Google Calendar",
        "category": "communication",
        "description": "Terminabgleich, Event-Entwürfe und freigabepflichtige Einladungen.",
        "owner_agent": "flow",
        "account_required": True,
        "cost": "Im vorhandenen Google-Konto kostenlos",
        "secret_groups": [["N8N_GOOGLE_CALENDAR_CREDENTIAL_ID"]],
        "configurable_keys": [
            "N8N_GOOGLE_CALENDAR_CREDENTIAL_ID",
            "N8N_CALENDAR_WEBHOOK_URL",
            "GOOGLE_CALENDAR_ID",
        ],
        "setup_steps": [
            "Google Calendar API im vorhandenen Google-Cloud-Projekt aktivieren.",
            "Eine separate Google-Calendar-OAuth-Credential in n8n verbinden.",
            "Testevent ohne Gäste erstellen; Einladungen bleiben freigabepflichtig.",
        ],
    },
    {
        "id": "quality_llm",
        "name": "Quality LLM",
        "category": "ai",
        "description": "Optionaler OpenAI-kompatibler Qualitätsanbieter mit Kostenlimit.",
        "owner_agent": "sage",
        "account_required": True,
        "cost": "Standardlimit 20 € pro Monat",
        "secret_groups": [["QUALITY_LLM_API_KEY"], ["QUALITY_LLM_BASE_URL"], ["QUALITY_LLM_MODEL"]],
        "configurable_keys": [
            "QUALITY_LLM_API_KEY",
            "QUALITY_LLM_BASE_URL",
            "QUALITY_LLM_MODEL",
            "QUALITY_LLM_MONTHLY_LIMIT_CENTS",
        ],
        "setup_steps": [
            "OpenAI-kompatiblen Anbieter auswählen und API-Key erzeugen.",
            "Base-URL, Modell und maximales Monatsbudget konfigurieren.",
            "Testaufruf ausführen; lokale Ausführung bleibt der Standard.",
        ],
    },
    {
        "id": "media_local",
        "name": "Lokale Medien-Pipeline",
        "category": "media",
        "description": "FFmpeg-basierte Video-, Audio-, Untertitel- und Exportpipeline.",
        "owner_agent": "aura",
        "account_required": False,
        "cost": "Kostenlos und lokal",
        "secret_groups": [],
        "configurable_keys": ["FFMPEG_PATH", "LOCAL_IMAGE_WEBHOOK_URL"],
        "setup_steps": [
            "FFmpeg lokal installieren.",
            "Optional eine lokale Bildgenerierungs-Pipeline als Webhook verbinden.",
            "Vertikale Exportprofile für Instagram und TikTok testen.",
        ],
    },
    {
        "id": "instagram",
        "name": "Instagram Publishing",
        "category": "social",
        "description": "Freigabepflichtige Reels und Posts für ein professionelles Konto.",
        "owner_agent": "flow",
        "account_required": True,
        "cost": "Plattformkonto kostenlos; Medienerzeugung separat",
        "secret_groups": [["INSTAGRAM_ACCESS_TOKEN"], ["INSTAGRAM_ACCOUNT_ID"]],
        "configurable_keys": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"],
        "setup_steps": [
            "Professionelles Instagram-Konto und Meta-App verbinden.",
            "Publishing-Berechtigungen freigeben und Testupload durchführen.",
            "Öffentliche Veröffentlichung nur nach Mission-Control-Freigabe erlauben.",
        ],
    },
    {
        "id": "tiktok",
        "name": "TikTok Draft Upload",
        "category": "social",
        "description": "Freigabepflichtiger Upload in den TikTok-Entwurfsfluss.",
        "owner_agent": "flow",
        "account_required": True,
        "cost": "TikTok-Developer-Konto kostenlos",
        "secret_groups": [["TIKTOK_CLIENT_KEY"], ["TIKTOK_CLIENT_SECRET"]],
        "configurable_keys": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
        "setup_steps": [
            "TikTok-Developer-App und Content Upload API konfigurieren.",
            "OAuth sowie video.upload-Berechtigung verbinden.",
            "Zunächst ausschließlich Entwurfsuploads verwenden.",
        ],
    },
    {
        "id": "commerce_browser",
        "name": "Kontrollierter Browser-Checkout",
        "category": "commerce",
        "description": "Produktsuche und Warenkorbvorbereitung; Kaufabschluss bleibt manuell.",
        "owner_agent": "atlas",
        "account_required": True,
        "cost": "Keine zusätzliche Plattformgebühr",
        "secret_groups": [],
        "configurable_keys": [],
        "setup_steps": [
            "Bestehende Browsersitzung verwenden; keine Passwörter speichern.",
            "Adresse, Zahlung und Gesamtpreis niemals in Agentenlogs übernehmen.",
            "Checkout erst nach Stufe-3-Freigabe dem Nutzer übergeben.",
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
    elif integration["id"] == "media_local":
        configured_path = os.getenv("FFMPEG_PATH", "").strip()
        detected = bool(
            (configured_path and os.path.isfile(configured_path))
            or shutil.which("ffmpeg")
        )
    elif integration["id"] == "commerce_browser":
        # No credentials are stored. Readiness means that the controlled handoff
        # workflow is available; login and checkout stay in the user's browser.
        detected = True

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
