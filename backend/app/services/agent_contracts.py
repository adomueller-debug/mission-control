from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContract:
    agent_id: str
    purpose: str
    required_artifact_types: tuple[str, ...]
    minimum_artifacts: int
    quality_rules: tuple[str, ...]


AGENT_CONTRACTS: dict[str, AgentContract] = {
    "research": AgentContract(
        agent_id="atlas",
        purpose="Belastbare Fakten, Quellen und klar markierte Annahmen liefern.",
        required_artifact_types=("research_report",),
        minimum_artifacts=1,
        quality_rules=(
            "Jede Tatsachenbehauptung muss einer tatsächlich geprüften Quelle zugeordnet sein.",
            "Nicht geprüfte Aussagen ausdrücklich als Annahme markieren.",
            "Konkrete nächste Entscheidung oder Übergabe angeben.",
        ),
    ),
    "design": AgentContract(
        agent_id="aura",
        purpose="Einen umsetzbaren Produkt- und Designvertrag erzeugen.",
        required_artifact_types=("design_brief", "design_tokens"),
        minimum_artifacts=2,
        quality_rules=(
            "User Journey, Informationshierarchie und Conversion-Ziel definieren.",
            "Farben, Typografie, Abstände, Komponenten und Motion-Verhalten konkretisieren.",
            "Mobile, Desktop, Accessibility und Reduced Motion berücksichtigen.",
        ),
    ),
    "business": AgentContract(
        agent_id="boss",
        purpose="Eine ausführbare Geschäftsempfehlung mit Annahmen und Kennzahlen liefern.",
        required_artifact_types=("decision_brief",),
        minimum_artifacts=1,
        quality_rules=(
            "Zielgruppe, Nutzenversprechen, Angebot, Risiken und nächste Aktion benennen.",
            "Keine Umsatz- oder Erfolgszusage erfinden.",
        ),
    ),
    "data": AgentContract(
        agent_id="orbit",
        purpose="Messbare Definitionen, Berechnungen und Datenquellen liefern.",
        required_artifact_types=("metric_spec",),
        minimum_artifacts=1,
        quality_rules=(
            "Für jede Kennzahl Formel, Einheit, Datenquelle und Aktualisierung definieren.",
            "Fehlende Daten sichtbar kennzeichnen.",
        ),
    ),
    "automation": AgentContract(
        agent_id="flow",
        purpose="Einen ausführbaren und fehlertoleranten Automationsvertrag liefern.",
        required_artifact_types=("workflow_spec",),
        minimum_artifacts=1,
        quality_rules=(
            "Trigger, Eingaben, Schritte, Ausgaben, Idempotenz und Fehlerpfade definieren.",
            "Außenwirkungen mit Risikostufe und Freigabe markieren.",
        ),
    ),
    "email": AgentContract(
        agent_id="flow",
        purpose="Einen vollständigen, versandfertigen E-Mail-Entwurf ohne Versand erzeugen.",
        required_artifact_types=("email_draft",),
        minimum_artifacts=1,
        quality_rules=(
            "Empfängerrolle, Betreff und vollständigen Nachrichtentext liefern.",
            "Fehlende Namen oder Fakten als offene Felder markieren, nicht erfinden.",
            "Versand bleibt eine separate freigabepflichtige Aktion.",
        ),
    ),
    "calendar": AgentContract(
        agent_id="flow",
        purpose="Einen vollständigen, idempotenten Kalenderentwurf ohne Einladung erzeugen.",
        required_artifact_types=("calendar_event_draft",),
        minimum_artifacts=1,
        quality_rules=(
            "Titel, Zeitraum, Zeitzone, Teilnehmer und Beschreibung strukturieren.",
            "Fehlende Angaben sichtbar lassen und keine Einladung versenden.",
        ),
    ),
    "security": AgentContract(
        agent_id="sentinel",
        purpose="Berechtigungen, Datenrisiken und Freigaben konkret prüfen.",
        required_artifact_types=("security_review",),
        minimum_artifacts=1,
        quality_rules=(
            "Secrets, personenbezogene Daten, Berechtigungen und Auditpflichten prüfen.",
            "Risiken nach Schweregrad und konkreter Abhilfe priorisieren.",
        ),
    ),
    "devops": AgentContract(
        agent_id="mercury",
        purpose="Einen reproduzierbaren Betriebs- oder Releaseplan liefern.",
        required_artifact_types=("operations_runbook",),
        minimum_artifacts=1,
        quality_rules=(
            "Deployment, Healthcheck, Rollback, Backup und Monitoring definieren.",
        ),
    ),
    "general": AgentContract(
        agent_id="boss",
        purpose="Das Ziel in ein belastbares Ergebnis oder eine ehrliche Blockade überführen.",
        required_artifact_types=("result_brief",),
        minimum_artifacts=1,
        quality_rules=("Fakten, Annahmen, Ergebnis und nächste Aktion trennen.",),
    ),
}


def contract_for(task_type: str) -> AgentContract:
    return AGENT_CONTRACTS.get(task_type, AGENT_CONTRACTS["general"])
