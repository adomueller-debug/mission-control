from __future__ import annotations

import os
from typing import Any

import requests

from backend.app.services.mission_router import mission_router
from backend.app.services.project_service import project_service
from backend.app.services.run_service import run_service


WEBSITE_SALES_PROFILE: dict[str, Any] = {
    "city": "Heidelberg",
    "target_revenue": 500,
    "preferred_industries": (
        "Alle Branchen, die lokal über eine Website Kunden gewinnen können; "
        "dynamisch nach Bedarf, Website-Defizit, Kontaktierbarkeit und Auftragswert priorisieren"
    ),
    "website_style": "minimalistisch, modern und clean",
    "color_direction": "modern, minimalistisch und clean; unternehmensspezifisch",
    "animation_style": (
        "sehr dynamisch und cineastisch mit scrollgebundenen Szenen, maskierten "
        "Übergängen, Parallax und mobiler Reduced-Motion-Alternative"
    ),
    "key_sections": (
        "Unternehmensspezifisch aus Google Maps, bestehender Website und weiteren "
        "öffentlichen Informationen ableiten"
    ),
    "offer_price": 350,
    "offer_min": 200,
    "offer_max": 500,
    "max_leads": 20,
    "outreach_channel": "E-Mail-Entwurf",
    "outreach_approval": False,
    "crm_spreadsheet_id": "1uCKDobkcfjjOOmRUGeUVCwtAW5ddw49Smo7nWz9hysY",
    "reference_folder_id": "1O-oENk03wkd6DcnWBVeiKBGocb4MQ5VL",
    "reference_video_ids": [
        "1xRcjUjZmaCYzU0-5dKdAAfzimvIssImn",
        "1UjVzKF4wIWt1eMBBxlguh_EoOwKPaWwv",
    ],
}

CODING_TERMS = {
    "api",
    "backend",
    "bug",
    "code",
    "dashboard",
    "datei",
    "frontend",
    "implementiere",
    "mission control",
    "refactor",
    "test",
}
WEBSITE_SALES_TERMS = {
    "500€",
    "euro",
    "heidelberg",
    "kunde",
    "lead",
    "lokale unternehmen",
    "umsatz",
    "verdiene",
    "verkauf",
    "website verkaufen",
    "websites verkaufen",
}
INTERNAL_TERMS = {
    "agenten",
    "agentenablauf",
    "button",
    "dashboard",
    "mission control",
    "operations",
    "oberfläche",
    "run-engine",
}


class OperationsRouter:
    def classify(self, task: str) -> dict[str, Any]:
        text = task.casefold()
        coding_matches = sorted(term for term in CODING_TERMS if term in text)
        sales_matches = sorted(term for term in WEBSITE_SALES_TERMS if term in text)
        if "mission control" in text or (coding_matches and not sales_matches):
            internal_matches = sorted(term for term in INTERNAL_TERMS if term in text)
            return {
                "kind": "coding",
                "workflow": "run_engine",
                "workstream": "internal" if internal_matches else "standalone",
                "confidence": 0.95 if "mission control" in text else 0.8,
                "signals": sorted(set(coding_matches + internal_matches)),
            }
        if sales_matches:
            return {
                "kind": "business",
                "workflow": "website_sales",
                "confidence": 0.9,
                "signals": sales_matches,
            }
        return {
            "kind": "business",
            "workflow": "mission_router",
            "confidence": 0.6,
            "signals": [],
        }

    def intake(
        self,
        *,
        task: str,
        workspace: str,
        options: dict[str, Any],
        answers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        route = self.classify(task)
        if route["kind"] == "coding":
            run = run_service.create(
                task=task,
                workspace=workspace,
                workstream=route.get("workstream", "standalone"),
                **options,
            )
            return {"status": "run_created", "route": route, "run": run}

        if route["workflow"] == "website_sales":
            payload = {**WEBSITE_SALES_PROFILE, **(answers or {}), "goal": task}
            # The current sales pilot never sends messages automatically.
            payload["outreach_approval"] = False
            result = self._send_to_n8n(payload)
            return {"route": route, **result}

        missing = self._generic_questions(answers or {})
        if missing:
            return {
                "status": "needs_input",
                "route": route,
                "message": "BOSS benötigt noch Kontext für einen belastbaren Missionsplan.",
                "questions": missing,
            }

        context = answers or {}
        name = str(context.get("project_name") or task).strip()[:120]
        project = project_service.create_project(
            name=name,
            description=str(context.get("desired_outcome", "")),
            goal=task,
            category="business",
            status="planning",
            workspace=workspace,
        )
        plan = mission_router.create_plan(project["id"], task)
        approved = mission_router.approve(plan["id"])
        return {
            "status": "project_created",
            "route": route,
            "project_id": project["id"],
            "mission_plan_id": approved["plan"]["id"],
            "task_count": len(approved["created_tasks"]),
            "message": "BOSS hat das Projekt geplant und delegiert.",
        }

    @staticmethod
    def _generic_questions(answers: dict[str, Any]) -> list[dict[str, Any]]:
        definitions = [
            (
                "project_name",
                "Wie soll das Projekt im Portfolio heißen?",
                "Kurzer, eindeutiger Projektname",
            ),
            (
                "desired_outcome",
                "Welches konkrete Ergebnis soll BOSS liefern lassen?",
                "Messbares Ergebnis oder fertiges Artefakt",
            ),
            (
                "target_audience",
                "Für wen ist das Ergebnis bestimmt?",
                "Zielgruppe, Nutzer oder Empfänger",
            ),
            (
                "external_action_policy",
                "Welche externen Aktionen dürfen vorbereitet oder ausgeführt werden?",
                "Zum Beispiel nur Entwürfe, keine Zahlungen, keine Veröffentlichung",
            ),
        ]
        return [
            {"field": field, "question": question, "placeholder": placeholder}
            for field, question, placeholder in definitions
            if not str(answers.get(field, "")).strip()
        ]

    @staticmethod
    def _send_to_n8n(payload: dict[str, Any]) -> dict[str, Any]:
        url = os.getenv(
            "N8N_WEBSITE_SALES_WEBHOOK_URL",
            "http://127.0.0.1:5678/webhook/mission-control-website-sales",
        )
        read_timeout = float(os.getenv("N8N_INTAKE_TIMEOUT_SECONDS", "60"))
        response = requests.post(url, json=payload, timeout=(5, read_timeout))
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("n8n hat keine gültige Missionsantwort geliefert.")
        return result


operations_router = OperationsRouter()
