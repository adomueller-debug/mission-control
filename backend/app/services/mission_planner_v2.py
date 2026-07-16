from __future__ import annotations

import re
from typing import Any


def build_mission_dag(goal: str) -> list[dict[str, Any]]:
    """Build a conservative, executable DAG when BOSS has no model plan yet."""
    lower = goal.casefold()
    coding = bool(re.search(r"website|webapp|app\b|code|dashboard|api|frontend|backend|button", lower))
    website = bool(re.search(r"website|landingpage|webseite", lower))
    email = bool(re.search(r"e-?mail|gmail|nachricht|anschreiben", lower))
    calendar = bool(re.search(r"kalender|termin|calendar|einladen", lower))
    research = bool(re.search(r"recherch|finde|suche|vergleich|markt|unternehmen", lower))
    data = bool(re.search(r"kpi|daten|analyse|report|tabelle|sheet|crm|leads", lower))

    items: list[dict[str, Any]] = []

    def add(
        key: str,
        title: str,
        agent: str,
        task_type: str,
        dependencies: list[str] | None = None,
        artifacts: list[str] | None = None,
        criteria: list[str] | None = None,
        risk: int = 0,
        resources: list[str] | None = None,
    ) -> None:
        items.append(
            {
                "key": key,
                "title": title,
                "description": goal,
                "agent_id": agent,
                "dependencies": dependencies or [],
                "required_tools": [task_type],
                "resource_keys": resources or [],
                "expected_artifacts": artifacts or [],
                "acceptance_criteria": criteria or ["Nachvollziehbares, strukturiertes Ergebnis"],
                "risk_level": risk,
                "max_attempts": 3,
            }
        )

    if coding:
        roots: list[str] = []
        if website or research:
            add("research", "Fakten und Referenzen verifizieren", "atlas", "research", artifacts=["research_report"], criteria=["Quellen oder klar markierte Annahmen"])
            roots.append("research")
        if website or re.search(r"ui|ux|design|oberfläche|layout", lower):
            add("design", "Designvertrag und User Journey erstellen", "aura", "design", artifacts=["design_brief", "design_tokens"], criteria=["Konkrete Tokens, Komponenten und visuelle Gates"])
            roots.append("design")
        add("blueprint", "Repository und technische Umsetzung planen", "forge_planner", "blueprint", roots, ["technical_blueprint"], ["Dateiplan, Testplan und Risiken vorhanden"])
        add("build", "Produkt gegen Blueprint implementieren", "forge_builder", "coding", ["blueprint"], ["code", "change_log"], ["Build und produktspezifische Gates ausführbar"], resources=["local-llm", "repository-write"])
        add("verify", "Produkt technisch und visuell prüfen", "forge_reviewer", "verification", ["build"], ["quality_report"], ["Alle erforderlichen Gates bestanden"])
        add("release", "Release Candidate erzeugen", "forge_publisher", "release", ["verify"], ["release_candidate"], ["Diff, Commit-Vorschlag und Releasebericht vorhanden"], risk=1)
    else:
        previous: list[str] = []
        if research:
            add("research", "Recherche mit Quellen durchführen", "atlas", "research", artifacts=["research_report"], criteria=["Quellen vorhanden und Annahmen gekennzeichnet"])
            previous = ["research"]
        if data:
            add("data", "Daten und Erfolgssignale strukturieren", "orbit", "data", previous, ["metric_spec"])
            previous = ["data"]
        office_items: list[str] = []
        if email:
            add("email", "Vollständigen E-Mail-Entwurf erstellen", "flow", "email", previous, ["email_draft"], ["Betreff und Nachricht vollständig; kein Versand"])
            office_items.append("email")
        if calendar:
            add("calendar", "Idempotenten Kalenderentwurf erstellen", "flow", "calendar", previous, ["calendar_event_draft"], ["Zeit, Zeitzone und Teilnehmer strukturiert; keine Einladung"])
            office_items.append("calendar")
        if office_items:
            add("security", "Empfänger, Rechte und Außenwirkung prüfen", "sentinel", "security", office_items, ["security_review"], ["Risikostufe und Freigabebedarf dokumentiert"])
        elif not items:
            add("delivery", "Ziel analysieren und nutzbares Ergebnis erstellen", "boss", "business", artifacts=["decision_brief"])

    return items
