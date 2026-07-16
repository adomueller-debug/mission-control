from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Protocol

import requests
from pydantic import BaseModel, Field


class SalesLead(BaseModel):
    id: str
    name: str
    category: str = "local_business"
    city: str = ""
    address: str = ""
    website: str = ""
    email: str = ""
    source_url: str
    website_score: int = Field(ge=0, le=100)
    opportunity_score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)


class LeadResearcher(Protocol):
    def find(self, city: str, limit: int) -> list[SalesLead]: ...


class LeadProcessor(Protocol):
    def store_and_draft(self, lead: SalesLead, draft: dict[str, str]) -> dict[str, Any]: ...


class OverpassLeadResearcher:
    endpoints = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    )

    def find(self, city: str, limit: int) -> list[SalesLead]:
        safe_city = re.sub(r"[^\w\säöüÄÖÜß.-]", "", city, flags=re.UNICODE).strip()
        if len(safe_city) < 2:
            raise ValueError("Ungültiger Ortsname")
        query = f"""
[out:json][timeout:35];
area["name"="{safe_city}"]["boundary"="administrative"]->.searchArea;
(
  nwr(area.searchArea)["name"]["shop"];
  nwr(area.searchArea)["name"]["craft"];
  nwr(area.searchArea)["name"]["amenity"~"restaurant|cafe|clinic|doctors|dentist|veterinary|pharmacy"];
  nwr(area.searchArea)["name"]["office"];
  nwr(area.searchArea)["name"]["beauty"];
);
out tags center {min(max(limit * 25, 250), 500)};
"""
        response = None
        last_error: requests.RequestException | None = None
        headers = {
            "User-Agent": "MissionControl/1.0 (local autonomous agent platform)",
            "Referer": "http://127.0.0.1:5173/",
        }
        for endpoint in self.endpoints:
            try:
                candidate = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=headers,
                    timeout=30,
                )
                candidate.raise_for_status()
                response = candidate
                break
            except requests.RequestException as exc:
                last_error = exc
        if response is None:
            raise last_error or requests.RequestException(
                "Keine öffentliche Overpass-Instanz erreichbar"
            )
        elements = response.json().get("elements", [])
        leads: list[SalesLead] = []
        seen: set[str] = set()
        for item in elements:
            tags = item.get("tags", {})
            name = str(tags.get("name", "")).strip()
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            website = str(tags.get("contact:website") or tags.get("website") or "").strip()
            email = str(tags.get("contact:email") or tags.get("email") or "").strip()
            category = str(
                tags.get("shop")
                or tags.get("craft")
                or tags.get("amenity")
                or tags.get("office")
                or "local_business"
            )
            address = " ".join(
                value
                for value in (
                    tags.get("addr:street"),
                    tags.get("addr:housenumber"),
                    tags.get("addr:postcode"),
                    tags.get("addr:city") or safe_city,
                )
                if value
            )
            website_score, opportunity_score, reasons = self._score(website, email)
            source_url = f"https://www.openstreetmap.org/{item.get('type', 'node')}/{item.get('id')}"
            lead_id = hashlib.sha256(f"{safe_city}:{name}:{address}".encode()).hexdigest()[:16]
            leads.append(
                SalesLead(
                    id=lead_id,
                    name=name,
                    category=category,
                    city=safe_city,
                    address=address,
                    website=website,
                    email=email,
                    source_url=source_url,
                    website_score=website_score,
                    opportunity_score=opportunity_score,
                    reasons=reasons,
                )
            )
        return sorted(leads, key=lambda lead: lead.opportunity_score, reverse=True)[:limit]

    @staticmethod
    def _score(website: str, email: str) -> tuple[int, int, list[str]]:
        reasons: list[str] = []
        website_score = 50
        opportunity = 25
        if not website:
            website_score = 0
            opportunity += 50
            reasons.append("Keine Website im öffentlichen Brancheneintrag hinterlegt")
        elif not website.startswith("https://"):
            website_score -= 15
            opportunity += 20
            reasons.append("Website ist nicht als HTTPS-Adresse hinterlegt")
        else:
            reasons.append("Bestehende Website benötigt eine manuelle UX-Prüfung")
        if email:
            opportunity += 20
            reasons.append("Öffentliche geschäftliche E-Mail vorhanden")
        else:
            reasons.append("Kein zulässiger E-Mail-Kontakt im Datensatz")
        return max(website_score, 0), min(opportunity, 100), reasons


class N8nLeadProcessor:
    def __init__(self, webhook_url: str | None = None):
        base = os.getenv("N8N_BASE_URL", "").rstrip("/")
        self.webhook_url = webhook_url or os.getenv(
            "N8N_SALES_LEAD_WEBHOOK_URL",
            f"{base}/webhook/mission-control-sales-lead" if base else "",
        )

    def store_and_draft(self, lead: SalesLead, draft: dict[str, str]) -> dict[str, Any]:
        if not self.webhook_url:
            return {
                "crm_logged": False,
                "draft_created": False,
                "sent": False,
                "detail": "N8N_SALES_LEAD_WEBHOOK_URL fehlt",
            }
        response = requests.post(
            self.webhook_url,
            json={"lead": lead.model_dump(), "draft": draft, "send": False},
            timeout=45,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("sent") is True:
            raise ValueError("Sales-Workflow darf E-Mails nur als Entwurf speichern.")
        return result


class WebsiteSalesPipeline:
    def execute(
        self,
        *,
        city: str = "Heidelberg",
        limit: int = 20,
        researcher: LeadResearcher | None = None,
        processor: LeadProcessor | None = None,
    ) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 20))
        leads = (researcher or OverpassLeadResearcher()).find(city, bounded_limit)
        processed = []
        for lead in leads:
            draft = self._draft(lead, city)
            if not lead.email:
                processed.append(
                    {
                        "lead": lead.model_dump(),
                        "crm_logged": False,
                        "draft_created": False,
                        "sent": False,
                        "approval_status": "not_contactable",
                        "draft": draft,
                    }
                )
                continue
            result = (processor or N8nLeadProcessor()).store_and_draft(lead, draft)
            processed.append(
                {
                    "lead": lead.model_dump(),
                    **result,
                    "sent": False,
                    "approval_status": "pending",
                    "draft": draft,
                }
            )
        return {
            "status": "awaiting_approval",
            "city": city,
            "lead_count": len(leads),
            "crm_logged_count": sum(bool(item.get("crm_logged")) for item in processed),
            "draft_count": sum(bool(item.get("draft_created")) for item in processed),
            "sent_count": 0,
            "approval_required": True,
            "leads": processed,
        }

    @staticmethod
    def _draft(lead: SalesLead, city: str) -> dict[str, str]:
        subject = f"Moderne Website-Idee für {lead.name}"
        body = (
            f"Guten Tag,\n\nbei der Recherche lokaler Unternehmen in {city} ist mir "
            f"{lead.name} aufgefallen. Ich habe eine unverbindliche Idee für eine moderne, "
            "schnelle Website mit klarer Kundenführung und hochwertigen Scroll-Animationen vorbereitet.\n\n"
            "Ein kompaktes Starterpaket liegt – abhängig vom Umfang – zwischen 200 und 500 EUR. "
            "Wenn das grundsätzlich interessant ist, sende ich gern zuerst einen unverbindlichen Entwurf.\n\n"
            "Freundliche Grüße\nAdrian Müller"
        )
        return {"to": lead.email, "subject": subject, "body": body}


website_sales_pipeline = WebsiteSalesPipeline()
