from __future__ import annotations

from typing import Any


AGENTS: list[dict[str, Any]] = [
    {
        "id": "boss",
        "name": "BOSS",
        "title": "CEO & Chief Orchestrator",
        "description": "Plant, priorisiert und delegiert Missionen im gesamten Agententeam.",
        "parent_id": None,
        "division": "command",
        "color": "gold",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.boss",
        "tools": ["project_planner", "task_graph", "agent_delegation", "architecture_decision"],
        "capabilities": ["project-planning", "prioritization", "delegation", "architecture-approval"],
        "delegates_to": ["forge", "aura", "sage"],
    },
    {
        "id": "forge",
        "name": "FORGE",
        "title": "Principal Software Engineer",
        "description": "Führt die technische Umsetzung und das Coding-Spezialistenteam.",
        "parent_id": "boss",
        "division": "engineering",
        "color": "orange",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.forge",
        "tools": ["filesystem", "shell", "git", "test_runner", "code_index"],
        "capabilities": ["backend", "frontend", "apis", "databases", "refactoring", "tests"],
        "delegates_to": ["forge_planner", "forge_builder", "forge_reviewer", "forge_publisher", "atlas"],
    },
    {
        "id": "aura",
        "name": "AURA",
        "title": "Head of Product & UX",
        "description": "Gestaltet Produkterlebnis, Designsystem und Nutzerführung.",
        "parent_id": "boss",
        "division": "product",
        "color": "violet",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.aura",
        "tools": ["ui_audit", "design_tokens", "component_catalog", "browser_preview"],
        "capabilities": ["ui", "ux", "user-journeys", "design-system", "branding"],
        "delegates_to": ["flow", "orbit", "forge_builder"],
    },
    {
        "id": "sage",
        "name": "SAGE",
        "title": "Chief AI Architect",
        "description": "Verantwortet Modelle, Agentenarchitektur, Memory und Tool Calling.",
        "parent_id": "boss",
        "division": "intelligence",
        "color": "cyan",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.sage",
        "tools": ["ollama", "prompt_lab", "mcp_registry", "memory_search", "rag_index"],
        "capabilities": ["llms", "prompt-engineering", "agents", "mcp", "memory", "rag", "tool-calling"],
        "delegates_to": ["sentinel", "atlas", "forge_builder"],
    },
    {
        "id": "atlas",
        "name": "ATLAS",
        "title": "Research & Knowledge Agent",
        "description": "Recherchiert, analysiert Dokumente und verwaltet belastbare Quellen.",
        "parent_id": "forge",
        "division": "knowledge",
        "color": "blue",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.atlas",
        "tools": ["web_search", "document_reader", "pdf_reader", "source_store"],
        "capabilities": ["research", "document-analysis", "pdf", "summarization", "citations"],
        "delegates_to": [],
    },
    {
        "id": "flow",
        "name": "FLOW",
        "title": "Automation Engineer",
        "description": "Entwickelt Workflows, Webhooks und robuste Integrationen.",
        "parent_id": "aura",
        "division": "automation",
        "color": "pink",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.flow",
        "tools": ["workflow_builder", "http_client", "webhook_tester", "n8n"],
        "capabilities": ["automation", "workflows", "apis", "webhooks", "integrations"],
        "delegates_to": ["forge_builder"],
    },
    {
        "id": "orbit",
        "name": "ORBIT",
        "title": "Data & Analytics Lead",
        "description": "Baut Datenprodukte, KPIs, Monitoring und Reporting.",
        "parent_id": "aura",
        "division": "data",
        "color": "emerald",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.orbit",
        "tools": ["sql", "postgresql", "qdrant", "metrics", "report_builder"],
        "capabilities": ["postgresql", "qdrant", "dashboards", "kpis", "reporting", "monitoring"],
        "delegates_to": ["forge_builder"],
    },
    {
        "id": "sentinel",
        "name": "SENTINEL",
        "title": "Security Engineer",
        "description": "Schützt Workspaces, Identitäten, Secrets und Audit-Trails.",
        "parent_id": "sage",
        "division": "security",
        "color": "red",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.sentinel",
        "tools": ["security_scanner", "secret_scanner", "permission_audit", "audit_log"],
        "capabilities": ["security", "authentication", "permissions", "secrets", "gdpr", "audit"],
        "delegates_to": ["mercury", "forge_builder"],
    },
    {
        "id": "mercury",
        "name": "MERCURY",
        "title": "DevOps Engineer",
        "description": "Betreibt CI/CD, Deployments, Backups und Infrastruktur.",
        "parent_id": "sentinel",
        "division": "infrastructure",
        "color": "indigo",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.mercury",
        "tools": ["docker", "git", "github_actions", "deployment", "backup"],
        "capabilities": ["docker", "ci-cd", "github", "deployment", "backups", "infrastructure"],
        "delegates_to": ["forge_publisher"],
    },
    {
        "id": "forge_planner",
        "name": "Blueprint",
        "title": "Software Planning Specialist",
        "description": "Analysiert Repositories und erstellt technische Implementierungspläne.",
        "parent_id": "forge",
        "division": "engineering",
        "color": "orange",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.forge.planner",
        "tools": ["code_index", "file_search", "task_graph"],
        "capabilities": ["repository-analysis", "task-decomposition", "file-selection"],
        "delegates_to": ["forge_builder"],
        "specialist": True,
    },
    {
        "id": "forge_builder",
        "name": "Builder",
        "title": "Coding Specialist",
        "description": "Implementiert präzise Änderungen im isolierten Workspace.",
        "parent_id": "forge",
        "division": "engineering",
        "color": "orange",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.forge.builder",
        "tools": ["filesystem", "write_patch", "shell", "code_index"],
        "capabilities": ["code-generation", "file-editing", "self-repair"],
        "delegates_to": ["forge_reviewer"],
        "specialist": True,
    },
    {
        "id": "forge_reviewer",
        "name": "Verifier",
        "title": "Quality & Review Specialist",
        "description": "Prüft Tests, Typen, Security und strukturelle Codequalität.",
        "parent_id": "forge",
        "division": "engineering",
        "color": "orange",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.forge.reviewer",
        "tools": ["pytest", "ruff", "mypy", "eslint", "change_reviewer"],
        "capabilities": ["test-validation", "static-analysis", "change-review"],
        "delegates_to": ["forge_builder", "forge_publisher"],
        "specialist": True,
    },
    {
        "id": "forge_publisher",
        "name": "Shipwright",
        "title": "Release Specialist",
        "description": "Veröffentlicht freigegebene Änderungen als abgesicherten Pull Request.",
        "parent_id": "forge",
        "division": "engineering",
        "color": "orange",
        "preferred_model": "qwen2.5:7b",
        "memory_namespace": "agents.forge.publisher",
        "tools": ["git", "github_pr", "github_auto_merge"],
        "capabilities": ["git", "github-pr", "auto-merge"],
        "delegates_to": [],
        "specialist": True,
    },
]

AGENT_BY_ID = {agent["id"]: agent for agent in AGENTS}

AGENT_STATUS_DEFINITIONS = {
    "offline": "Agent ist derzeit nicht aktiv.",
    "waiting": "Agent wartet auf eine geplante Übergabe.",
    "active": "Agent bearbeitet aktuell eine Aufgabe.",
    "completed": "Agent hat seinen Schritt erfolgreich abgeschlossen.",
    "skipped": "Agent wurde für diesen Run nicht benötigt.",
    "blocked": "Agent kann ohne externe Änderung nicht fortfahren.",
    "paused": "Agent wurde durch einen Abbruch oder eine Pause angehalten.",
    "error": "Agentenschritt ist mit einem Fehler beendet worden.",
}

LEGACY_AGENT_ALIASES = {
    "general": "boss",
    "orchestrator": "boss",
    "planner": "forge_planner",
    "coder": "forge_builder",
    "builder": "forge_builder",
    "analyst": "forge_reviewer",
    "reviewer": "forge_reviewer",
    "validator": "forge_reviewer",
    "publisher": "forge_publisher",
    "github": "forge_publisher",
}

STEP_TO_AGENT = {
    "planner": "boss",
    "technical_planner": "forge_planner",
    "coder": "forge_builder",
    "validator": "forge_reviewer",
    "reviewer": "forge_reviewer",
    "github": "forge_publisher",
}

RUN_SEQUENCE = [
    "boss",
    "forge_planner",
    "forge_builder",
    "forge_reviewer",
    "forge_publisher",
]


def canonical_agent_id(agent_id: str) -> str:
    return LEGACY_AGENT_ALIASES.get(agent_id, agent_id)


def get_agent(agent_id: str) -> dict[str, Any] | None:
    return AGENT_BY_ID.get(canonical_agent_id(agent_id))


def can_delegate(from_agent: str, to_agent: str) -> bool:
    source = get_agent(from_agent)
    return bool(source and canonical_agent_id(to_agent) in source["delegates_to"])


def agent_roster(run: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    current_step = run.get("current_step") if run else None
    active = (
        STEP_TO_AGENT.get(current_step, current_step)
        if isinstance(current_step, str)
        else None
    )
    status = run.get("status") if run else None
    specialized = bool(run and run.get("run_kind", "coding") != "coding")
    active_index = RUN_SEQUENCE.index(active) if active in RUN_SEQUENCE else -1
    roster: list[dict[str, Any]] = []

    for agent in AGENTS:
        agent_status = "offline"
        agent_id = agent["id"]
        if specialized and agent_id == active:
            if status == "completed":
                agent_status = "completed"
            elif status == "failed":
                agent_status = "error"
            elif status == "cancelled":
                agent_status = "paused"
            else:
                agent_status = "active"
        elif run and agent_id in RUN_SEQUENCE and not specialized:
            index = RUN_SEQUENCE.index(agent_id)
            if status == "completed":
                agent_status = (
                    "skipped"
                    if agent_id == "forge_publisher" and not run.get("publish")
                    else "completed"
                )
            elif status in {"failed", "cancelled"} and agent_id == active:
                agent_status = "error" if status == "failed" else "paused"
            elif agent_id == active:
                agent_status = "active"
            elif active_index > index:
                agent_status = "completed"
            else:
                agent_status = "waiting"

        if agent_id == "forge" and not specialized:
            child_states = [
                item["status"]
                for item in roster
                if item.get("parent_id") == "forge" and item.get("specialist")
            ]
            if status == "failed" and active and active.startswith("forge_"):
                agent_status = "error"
            elif status == "cancelled" and active and active.startswith("forge_"):
                agent_status = "paused"
            elif active and active.startswith("forge_"):
                agent_status = "active"
            elif status == "completed":
                agent_status = "completed"
            elif any(child == "completed" for child in child_states):
                agent_status = "completed"

        legacy_ids = [
            alias
            for alias, canonical in LEGACY_AGENT_ALIASES.items()
            if canonical == agent_id
        ]
        roster.append({**agent, "legacy_ids": legacy_ids, "status": agent_status})
    return roster
