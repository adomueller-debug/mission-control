from __future__ import annotations

import os
import smtplib
import ssl
from typing import Any

import requests

from backend.app.services.github_auth import github_auth_status
from backend.app.services.integration_catalog import INTEGRATION_BY_ID


def _result(integration_id: str, ok: bool, detail: str, **metadata: Any) -> dict[str, Any]:
    return {
        "id": integration_id,
        "ok": ok,
        "detail": detail,
        "metadata": metadata,
    }


def _recent_node_auth_failure(
    base: str,
    headers: dict[str, str],
    workflow_id: str,
    node_name: str,
) -> dict[str, str] | None:
    """Return the latest relevant auth failure instead of trusting attached credentials."""
    response = requests.get(
        f"{base}/api/v1/executions",
        params={"workflowId": workflow_id, "limit": "10", "includeData": "true"},
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    for execution in response.json().get("data", []):
        result_data = execution.get("data", {}).get("resultData", {})
        if execution.get("status") == "success":
            return None
        if result_data.get("lastNodeExecuted") != node_name:
            continue
        error = result_data.get("error") or {}
        message = str(error.get("message", ""))
        description = str(error.get("description", ""))
        combined = f"{message} {description}".lower()
        if any(
            marker in combined
            for marker in (
                "authentication failed",
                "invalid_client",
                "client secret",
                "unauthorized",
            )
        ):
            return {
                "execution_id": str(execution.get("id", "")),
                "error_type": str(error.get("name") or "OAuthError"),
            }
        return None
    return None


def verify_integration(integration_id: str) -> dict[str, Any]:
    if integration_id not in INTEGRATION_BY_ID:
        raise ValueError(f"Unbekannte Integration: {integration_id}")
    try:
        if integration_id == "ollama":
            base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
            response = requests.get(
                base.rsplit("/api/", 1)[0] + "/api/tags", timeout=5
            )
            response.raise_for_status()
            return _result(
                integration_id,
                True,
                "Ollama ist erreichbar.",
                models=len(response.json().get("models", [])),
            )

        if integration_id == "github":
            status = github_auth_status(verify=True)
            return _result(
                integration_id,
                bool(status["verified"]),
                "GitHub API-Zugang ist gültig."
                if status["verified"]
                else "GitHub API-Zugang konnte nicht verifiziert werden.",
                login=status["login"],
            )

        if integration_id == "smtp":
            gmail_credential_id = os.getenv("N8N_GMAIL_CREDENTIAL_ID")
            if gmail_credential_id:
                base = os.environ["N8N_BASE_URL"].rstrip("/")
                response = requests.get(
                    f"{base}/api/v1/workflows",
                    params={"limit": 1},
                    headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"]},
                    timeout=10,
                )
                response.raise_for_status()
                return _result(
                    integration_id,
                    True,
                    "Gmail OAuth ist in n8n verbunden; Mission Control erstellt ausschließlich Entwürfe.",
                    provider="gmail_oauth",
                    draft_only=True,
                )
            host = os.environ["SMTP_HOST"]
            port = int(os.getenv("SMTP_PORT", "587"))
            username = os.environ["SMTP_USERNAME"]
            password = "".join(os.environ["SMTP_PASSWORD"].split())
            with smtplib.SMTP(host, port, timeout=15) as client:
                client.ehlo()
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
                client.login(username, password)
            return _result(
                integration_id,
                True,
                "SMTP-Anmeldung ist gültig; es wurde keine E-Mail versendet.",
                username=username,
                host=host,
                port=port,
            )

        if integration_id == "n8n":
            base = os.environ["N8N_BASE_URL"].rstrip("/")
            health = requests.get(f"{base}/healthz", timeout=5)
            api = requests.get(
                f"{base}/api/v1/workflows",
                params={"limit": 1},
                headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"]},
                timeout=10,
            )
            ok = health.status_code == 200 and api.status_code == 200
            return _result(
                integration_id,
                ok,
                "n8n Health und API-Zugang sind gültig."
                if ok
                else "n8n ist erreichbar, aber der API-Zugang wurde abgelehnt.",
                health_status=health.status_code,
                api_status=api.status_code,
            )

        if integration_id == "google_workspace":
            spreadsheet_id = os.environ["GOOGLE_SHEETS_CRM_SPREADSHEET_ID"]
            drive_folder_id = os.environ["GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID"]
            credential_id = os.environ["N8N_GOOGLE_SHEETS_CREDENTIAL_ID"]
            base = os.environ["N8N_BASE_URL"].rstrip("/")
            workflow_id = os.getenv(
                "N8N_SALES_LEAD_WORKFLOW_ID",
                os.getenv("N8N_WEBSITE_SALES_WORKFLOW_ID", "yxfpYotV3cTW4zbf"),
            )
            headers = {"X-N8N-API-KEY": os.environ["N8N_API_KEY"]}
            response = requests.get(
                f"{base}/api/v1/workflows/{workflow_id}",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            workflow = response.json()
            sheets_nodes = [
                node
                for node in workflow.get("nodes", [])
                if node.get("type") == "n8n-nodes-base.googleSheets"
            ]
            credential_attached = any(
                node.get("credentials", {})
                .get("googleSheetsOAuth2Api", {})
                .get("id")
                == credential_id
                for node in sheets_nodes
            )
            ok = bool(
                spreadsheet_id
                and drive_folder_id
                and workflow.get("active")
                and credential_attached
            )
            auth_failure = (
                _recent_node_auth_failure(
                    base,
                    headers,
                    workflow_id,
                    "Append Lead to CRM",
                )
                if ok
                else None
            )
            if auth_failure:
                ok = False
            return _result(
                integration_id,
                ok,
                (
                    "Google Drive, CRM-Sheet und n8n-OAuth sind verdrahtet."
                    if ok
                    else (
                        "Google OAuth ist verdrahtet, aber der letzte echte Sheets-Aufruf wurde abgelehnt. Client-ID und Client-Secret in n8n neu setzen und den Account erneut autorisieren."
                        if auth_failure
                        else "Google-IDs sind gesetzt, aber n8n-OAuth ist noch nicht am aktiven Workflow verdrahtet."
                    )
                ),
                workflow_active=bool(workflow.get("active")),
                sheets_node_count=len(sheets_nodes),
                credential_attached=credential_attached,
                oauth_action_required=bool(auth_failure),
                **(auth_failure or {}),
            )

        environment = os.getenv("PAYPAL_ENVIRONMENT", "sandbox").lower()
        base = (
            "https://api-m.paypal.com"
            if environment == "live"
            else "https://api-m.sandbox.paypal.com"
        )
        credentials = (
            os.environ["PAYPAL_CLIENT_ID"],
            os.environ["PAYPAL_CLIENT_SECRET"],
        )
        response = requests.post(
            f"{base}/v1/oauth2/token",
            auth=credentials,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        ok = response.status_code == 200
        detected_environment = environment
        if not ok:
            other_environment = "live" if environment == "sandbox" else "sandbox"
            other_base = (
                "https://api-m.paypal.com"
                if other_environment == "live"
                else "https://api-m.sandbox.paypal.com"
            )
            other_response = requests.post(
                f"{other_base}/v1/oauth2/token",
                auth=credentials,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials"},
                timeout=15,
            )
            if other_response.status_code == 200:
                detected_environment = other_environment
        return _result(
            integration_id,
            ok,
            "PayPal OAuth-Zugang ist gültig."
            if ok
            else (
                f"PayPal-Zugang gehört zur Umgebung {detected_environment}, "
                f"konfiguriert ist aber {environment}."
                if detected_environment != environment
                else "PayPal hat die Zugangsdaten abgelehnt."
            ),
            environment=environment,
            detected_environment=detected_environment,
            status=response.status_code,
        )
    except (KeyError, ValueError):
        return _result(
            integration_id, False, "Erforderliche Konfiguration fehlt oder ist ungültig."
        )
    except (OSError, requests.RequestException, smtplib.SMTPException) as exc:
        return _result(
            integration_id,
            False,
            "Verbindungsprüfung fehlgeschlagen.",
            error_type=type(exc).__name__,
        )
