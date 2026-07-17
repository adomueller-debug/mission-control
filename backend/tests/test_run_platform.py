from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.core.workspace_security import (
    WorkspaceViolation,
    resolve_workspace_path,
)
from backend.app.database.database import SessionLocal
from backend.app.core.version import MISSION_CONTROL_VERSION
from backend.app.main import app
from backend.app.models.run import (
    AgentDelegation,
    AgentMemoryEntry,
    AgentRun,
    RunCheckpoint,
    RunEvent,
)
from backend.app.models.project import Project, ProjectArtifact, ProjectTask
from backend.app.models.mission import (
    IntegrationRequirement,
    MissionPlan,
    MissionPlanTask,
)
from backend.app.models.execution_plan import ExecutionPlan, PlanStep
from backend.app.services import run_engine as run_engine_module
from backend.app.services import github_publisher as publisher_module
from backend.app.services import integration_verifier as integration_verifier_module
from backend.app.services import validator as validator_module
from backend.app.services.agent_catalog import agent_roster
from backend.app.services.agent_team import agent_team
from backend.app.services.change_service import change_service
from backend.app.services.coder import _parse_output
from backend.app.services.file_selector import select_relevant_files
from backend.app.services.run_service import run_service
from backend.app.services.reviewer import review_changes
from backend.app.services.mission_router import mission_router
from backend.app.services.operations_router import operations_router
from backend.app.services.planner import create_execution_plan
from backend.app.services.project_service import project_service
from backend.app.services.specialized_run_engine import (
    SpecializedArtifact,
    SpecializedTaskOutput,
    specialized_run_engine,
)
from backend.app.services.website_sales_pipeline import SalesLead, WebsiteSalesPipeline


@pytest.fixture(autouse=True)
def clean_runs():
    yield
    with SessionLocal() as db:
        db.execute(delete(MissionPlanTask))
        db.execute(delete(MissionPlan))
        db.execute(delete(IntegrationRequirement))
        db.execute(delete(ProjectArtifact))
        db.execute(delete(ProjectTask))
        db.execute(delete(Project))
        db.execute(delete(AgentMemoryEntry))
        db.execute(delete(AgentDelegation))
        db.execute(delete(RunCheckpoint))
        db.execute(delete(RunEvent))
        db.execute(delete(AgentRun))
        db.commit()


def test_integration_center_exposes_secret_status_without_values(
    tmp_path: Path, monkeypatch
):
    secret_file = tmp_path / "mission-control.env"
    monkeypatch.setenv("MISSION_CONTROL_ENV_FILE", str(secret_file))
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_USERNAME", "agent@example.test")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("N8N_GMAIL_CREDENTIAL_ID", raising=False)
    with TestClient(app) as client:
        catalog = client.get("/api/v1/integrations")
        assert catalog.status_code == 200
        smtp = next(item for item in catalog.json() if item["id"] == "smtp")
        assert smtp["ready"] is False
        assert [item["configured"] for item in smtp["secrets"]] == [False]
        assert "smtp.example.test" not in str(smtp)

        saved = client.post(
            "/api/v1/integrations/smtp/configuration",
            json={"values": {"SMTP_PASSWORD": "local-test-secret"}},
        )
        assert saved.status_code == 200
        assert saved.json()["saved_keys"] == ["SMTP_PASSWORD"]
        assert "local-test-secret" not in str(saved.json())
        assert "local-test-secret" in secret_file.read_text(encoding="utf-8")

        rejected = client.post(
            "/api/v1/integrations/smtp/configuration",
            json={"values": {"UNSAFE_KEY": "value"}},
        )
        assert rejected.status_code == 400

        project = client.post(
            "/api/v1/projects",
            json={"name": "Sales System", "workspace": str(tmp_path)},
        ).json()
        requirement = client.post(
            f"/api/v1/projects/{project['id']}/integration-requirements",
            json={
                "integration_id": "smtp",
                "purpose": "Freigegebene Kundenkommunikation",
            },
        )
        assert requirement.status_code == 201
        assert requirement.json()["purpose"] == "Freigegebene Kundenkommunikation"
        assert client.get(
            f"/api/v1/projects/{project['id']}/integration-requirements"
        ).json()[0]["integration_id"] == "smtp"


def test_gmail_oauth_verification_does_not_require_smtp_password(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

    monkeypatch.setenv("N8N_GMAIL_CREDENTIAL_ID", "gmail-credential")
    monkeypatch.setenv("N8N_BASE_URL", "http://n8n.test")
    monkeypatch.setenv("N8N_API_KEY", "local-api-key")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(
        integration_verifier_module.requests,
        "get",
        lambda *args, **kwargs: Response(),
    )

    result = integration_verifier_module.verify_integration("smtp")

    assert result["ok"] is True
    assert result["metadata"] == {"provider": "gmail_oauth", "draft_only": True}


def test_google_workspace_verification_reports_real_oauth_failure(monkeypatch):
    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    monkeypatch.setenv("GOOGLE_SHEETS_CRM_SPREADSHEET_ID", "sheet-id")
    monkeypatch.setenv("GOOGLE_DRIVE_AI_PLATFORM_FOLDER_ID", "folder-id")
    monkeypatch.setenv("N8N_GOOGLE_SHEETS_CREDENTIAL_ID", "sheets-credential")
    monkeypatch.setenv("N8N_SALES_LEAD_WORKFLOW_ID", "sales-workflow")
    monkeypatch.setenv("N8N_BASE_URL", "http://n8n.test")
    monkeypatch.setenv("N8N_API_KEY", "local-api-key")

    def fake_get(url, **kwargs):
        if url.endswith("/api/v1/workflows/sales-workflow"):
            return Response(
                {
                    "active": True,
                    "nodes": [
                        {
                            "type": "n8n-nodes-base.googleSheets",
                            "credentials": {
                                "googleSheetsOAuth2Api": {
                                    "id": "sheets-credential"
                                }
                            },
                        }
                    ],
                }
            )
        return Response(
            {
                "data": [
                    {
                        "id": "4",
                        "status": "error",
                        "data": {
                            "resultData": {
                                "lastNodeExecuted": "Append Lead to CRM",
                                "error": {
                                    "name": "NodeApiError",
                                    "message": "Client authentication failed",
                                    "description": "invalid_client: client secret is invalid",
                                },
                            }
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr(integration_verifier_module.requests, "get", fake_get)

    result = integration_verifier_module.verify_integration("google_workspace")

    assert result["ok"] is False
    assert result["metadata"]["credential_attached"] is True
    assert result["metadata"]["oauth_action_required"] is True
    assert result["metadata"]["execution_id"] == "4"
    assert "Client-ID und Client-Secret" in result["detail"]


def test_specialized_executor_persists_structured_result(tmp_path: Path, monkeypatch):
    output = SpecializedTaskOutput(
        summary="Research abgeschlossen",
        findings=["Öffentlicher Bedarf ist dokumentiert"],
        artifacts=[
            SpecializedArtifact(
                title="Research Brief",
                content=(
                    "Belastbares Rechercheergebnis mit klar getrennten Fakten, Annahmen, "
                    "Quellenbezug, Entscheidungskontext und einem konkreten nächsten Schritt. "
                    "Die Quelle wurde für diesen Test explizit angegeben und die Aussage bleibt "
                    "auf den dokumentierten Bedarf begrenzt. BOSS kann das Ergebnis priorisieren."
                ),
                artifact_type="research_report",
            )
        ],
        next_actions=["Ergebnis durch BOSS priorisieren"],
        sources=["https://example.test/source"],
    )
    monkeypatch.setattr(
        specialized_run_engine,
        "_execute_task",
        lambda task_type, task, agent: (output, "test.executor"),
    )
    run = run_service.create(
        task="Recherchiere den lokalen Markt",
        workspace=str(tmp_path),
        run_kind="task:research",
        start=False,
    )

    specialized_run_engine.execute(run["id"])

    completed = run_service.get(run["id"])
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["run_kind"] == "task:research"
    assert completed["result"]["executor"] == {
        "task_type": "research",
        "agent": "atlas",
    }
    assert completed["result"]["artifacts"][0]["title"] == "Research Brief"


def test_specialized_executor_rejects_missing_role_contract_artifacts():
    output = SpecializedTaskOutput(
        summary="Design ist angeblich fertig",
        artifacts=[
            SpecializedArtifact(
                title="Lose Notiz",
                content="Eine nicht umsetzbare Designnotiz.",
                artifact_type="document",
            )
        ],
    )

    validation = specialized_run_engine._validate_result("design", output)

    assert validation["success"] is False
    failed = {
        item["name"] for item in validation["checks"] if not item["success"]
    }
    assert failed == {
        "minimum-artifacts",
        "required-artifact-types",
        "artifact-substance",
        "contract-semantics",
    }


def test_specialized_executor_normalizes_one_substantive_generic_artifact():
    output = SpecializedTaskOutput(
        summary="Lokaler Markt wurde mit nachvollziehbarer Methode untersucht.",
        findings=["Öffentliche Brancheneinträge wurden getrennt von Annahmen bewertet."],
        artifacts=[
            SpecializedArtifact(
                title="Research Brief",
                content=(
                    "Die Recherche dokumentiert Datenquelle, Methode, Bedarfssignale, "
                    "Einschränkungen und die nächste manuelle Prüfung. Jeder Eintrag besitzt "
                    "eine öffentliche Quelladresse. Ein fehlender Website-Link wird ausdrücklich "
                    "nur als Signal und nicht als Beweis gewertet. Vor einer Kontaktaufnahme "
                    "müssen Website und geschäftliche E-Mail erneut verifiziert werden."
                ),
                artifact_type="document",
            )
        ],
        sources=["https://www.openstreetmap.org/node/1"],
    )

    normalized = specialized_run_engine._canonicalize_artifact_types(
        "research", output
    )

    assert normalized.artifacts[0].artifact_type == "research_report"
    assert specialized_run_engine._validate_result("research", normalized)["success"]


def test_atlas_uses_real_overpass_tool_for_local_lead_research(monkeypatch):
    lead = SalesLead(
        id="lead-1",
        name="Heidelberger Beispielbetrieb",
        city="Heidelberg",
        source_url="https://www.openstreetmap.org/node/1",
        website_score=0,
        opportunity_score=75,
        reasons=["Keine Website im öffentlichen Brancheneintrag hinterlegt"],
    )
    monkeypatch.setattr(
        "backend.app.services.specialized_run_engine.OverpassLeadResearcher.find",
        lambda self, city, limit: [lead],
    )

    result, tool = specialized_run_engine._execute_task(
        "research",
        "Priorisiere Unternehmen in Heidelberg mit fehlender Website für das CRM.",
        "atlas",
    )

    assert tool == "openstreetmap.overpass"
    assert result.artifacts[0].artifact_type == "research_report"
    assert result.sources == [lead.source_url]
    assert specialized_run_engine._validate_result("research", result)["success"]


def test_task_schema_constrains_artifact_type_for_ollama():
    schema = specialized_run_engine._output_schema("research")
    artifact_type = schema["$defs"]["SpecializedArtifact"]["properties"][
        "artifact_type"
    ]

    assert artifact_type["enum"] == ["research_report"]
    assert "default" not in artifact_type


def test_website_sales_pipeline_researches_scores_logs_and_drafts_without_sending():
    class Researcher:
        def find(self, city: str, limit: int):
            assert city == "Heidelberg"
            assert limit == 20
            return [
                SalesLead(
                    id="lead-1",
                    name="Beispielbetrieb",
                    email="kontakt@example.test",
                    source_url="https://www.openstreetmap.org/node/1",
                    website_score=10,
                    opportunity_score=90,
                    reasons=["Keine moderne Website"],
                ),
                SalesLead(
                    id="lead-2",
                    name="Ohne Kontakt",
                    source_url="https://www.openstreetmap.org/node/2",
                    website_score=0,
                    opportunity_score=70,
                    reasons=["Keine Website"],
                ),
            ]

    class Processor:
        def store_and_draft(self, lead, draft):
            assert lead.id == "lead-1"
            assert draft["to"] == "kontakt@example.test"
            return {"crm_logged": True, "draft_created": True, "sent": False}

    result = WebsiteSalesPipeline().execute(
        researcher=Researcher(), processor=Processor()
    )

    assert result["status"] == "awaiting_approval"
    assert result["lead_count"] == 2
    assert result["crm_logged_count"] == 1
    assert result["draft_count"] == 1
    assert result["sent_count"] == 0
    assert result["approval_required"] is True
    assert result["leads"][0]["approval_status"] == "pending"
    assert result["leads"][1]["approval_status"] == "not_contactable"


def test_boss_mission_router_creates_reviewable_plan_and_materializes_tasks(
    tmp_path: Path, monkeypatch
):
    def fail_ollama(goal, project):
        raise ValueError("offline")

    monkeypatch.setattr(mission_router, "_ollama_plan", fail_ollama)
    autopilot_projects = []
    monkeypatch.setattr(
        project_service,
        "enable_autopilot",
        lambda project_id: autopilot_projects.append(project_id),
    )
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={
                "name": "Websites verkaufen",
                "goal": "Lokalen Unternehmen bessere Websites verkaufen",
                "category": "business",
                "workspace": str(tmp_path),
            },
        ).json()
        response = client.post(
            f"/api/v1/projects/{project['id']}/mission-plans", json={}
        )
        assert response.status_code == 201
        plan = response.json()
        assert plan["planner_mode"] == "fallback"
        assert plan["status"] == "draft"
        assert {task["agent_id"] for task in plan["tasks"]} >= {
            "atlas",
            "aura",
            "forge",
            "flow",
            "sentinel",
            "orbit",
        }
        flow = next(task for task in plan["tasks"] if task["agent_id"] == "flow")
        assert flow["delegation_path"] == ["boss", "aura", "flow"]

        approved = client.post(f"/api/v1/mission-plans/{plan['id']}/approve")
        assert approved.status_code == 200
        result = approved.json()
        assert result["plan"]["status"] == "approved"
        assert len(result["created_tasks"]) == len(plan["tasks"])
        assert {item["integration_id"] for item in result["integration_requirements"]} >= {
            "github",
            "smtp",
            "paypal",
            "n8n",
            "google_workspace",
        }
        refreshed = client.get(f"/api/v1/projects/{project['id']}").json()
        assert refreshed["task_counts"]["planned"] == len(plan["tasks"])
        assert autopilot_projects == [project["id"]]
        tasks_by_id = {task["id"]: task for task in refreshed["tasks"]}
        for task in refreshed["tasks"]:
            assert all(dependency in tasks_by_id for dependency in task["dependencies"])


def test_project_autopilot_can_be_started_and_paused(tmp_path: Path, monkeypatch):
    spawned = []
    monkeypatch.setattr(
        project_service,
        "_spawn_autopilot",
        lambda project_id: spawned.append(project_id),
    )
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "Autonomous project", "workspace": str(tmp_path)},
        ).json()
        task = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={
                "title": "Research the market",
                "task_type": "research",
                "assigned_agent": "atlas",
            },
        ).json()

        started = client.post(
            f"/api/v1/projects/{project['id']}/autopilot/start"
        )
        assert started.status_code == 202
        assert started.json()["autopilot_enabled"] is True
        assert started.json()["status"] == "active"
        assert spawned == [project["id"]]

        stopped = client.post(
            f"/api/v1/projects/{project['id']}/autopilot/stop"
        )
        assert stopped.status_code == 200
        assert stopped.json()["autopilot_enabled"] is False
        assert stopped.json()["status"] == "paused"

        project_service.update_task(task["id"], {"status": "blocked"})
        resumed = client.post(
            f"/api/v1/projects/{project['id']}/autopilot/start"
        )
        assert resumed.status_code == 202
        assert resumed.json()["tasks"][0]["status"] == "planned"
        assert spawned == [project["id"], project["id"]]


def test_operations_router_sends_website_sales_to_n8n_with_saved_profile(
    tmp_path: Path, monkeypatch
):
    captured = {}
    sent = threading.Event()

    def fake_send(payload):
        captured.update(payload)
        sent.set()
        return {
            "status": "project_created",
            "project_id": "project-from-n8n",
            "mission_plan_id": "plan-from-n8n",
            "task_count": 6,
        }

    monkeypatch.setattr(operations_router, "_send_to_n8n", fake_send)
    monkeypatch.setattr(
        operations_router,
        "_dispatch_website_mission",
        lambda project_id, _task, payload: fake_send(
            {**payload, "project_id": project_id}
        ),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/intake",
            json={
                "task": "Verdiene 500€ mit Websites für lokale Unternehmen in Heidelberg",
                "workspace": str(tmp_path),
            },
        )

    assert response.status_code == 202
    assert response.json()["route"]["workflow"] == "website_sales"
    assert response.json()["status"] == "project_created"
    assert response.json()["phase"] == "planning"
    assert response.json()["project_id"] != "project-from-n8n"
    assert sent.wait(2)
    assert captured["project_id"] == response.json()["project_id"]
    assert captured["max_leads"] == 20
    assert captured["offer_min"] == 200
    assert captured["offer_max"] == 500
    assert captured["outreach_channel"] == "E-Mail-Entwurf"
    assert captured["outreach_approval"] is False
    assert "Alle Branchen" in captured["preferred_industries"]
    assert "cineastisch" in captured["animation_style"]


def test_operations_intake_accepts_project_while_n8n_times_out_in_background(
    tmp_path: Path, monkeypatch
):
    attempted = threading.Event()

    def timeout(_payload):
        attempted.set()
        raise requests.ReadTimeout("n8n is still processing")

    monkeypatch.setattr(operations_router, "_send_to_n8n", timeout)
    def dispatch(_project_id, _task, payload):
        try:
            timeout(payload)
        except requests.ReadTimeout:
            pass

    monkeypatch.setattr(operations_router, "_dispatch_website_mission", dispatch)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/intake",
            json={
                "task": "Finde Website-Leads in Heidelberg",
                "workspace": str(tmp_path),
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "project_created"
    assert attempted.wait(2)
    with TestClient(app) as client:
        project = client.get(f"/api/v1/projects/{response.json()['project_id']}")
    assert project.status_code == 200


def test_operations_router_keeps_mission_control_changes_on_coding_engine(
    tmp_path: Path, monkeypatch
):
    expected = {"id": "run-1", "status": "queued"}
    captured = {}

    def create_run(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(run_service, "create", create_run)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/intake",
            json={
                "task": "Implementiere im Mission Control Dashboard eine neue API-Ansicht",
                "workspace": str(tmp_path),
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "run_created"
    assert response.json()["route"]["workflow"] == "run_engine"
    assert response.json()["route"]["workstream"] == "internal"
    assert response.json()["run"] == expected
    assert captured["workstream"] == "internal"


def test_operations_router_collects_context_for_unknown_business_mission(
    tmp_path: Path,
):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/intake",
            json={
                "task": "Baue ein neues Geschäftsfeld auf",
                "workspace": str(tmp_path),
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "needs_input"
    assert {item["field"] for item in response.json()["questions"]} == {
        "project_name",
        "desired_outcome",
        "target_audience",
        "external_action_policy",
    }


def test_business_workflow_combines_intake_crm_gmail_and_delivery():
    workflow_path = (
        Path(__file__).resolve().parents[2]
        / "n8n"
        / "workflows"
        / "mission-control-business-automation.json"
    )
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    nodes = {node["name"]: node for node in workflow["nodes"]}
    normalize = nodes["Normalize Mission & Build Questions"]["parameters"]["jsCode"]
    sheets = nodes["Log Mission in Google Sheets CRM"]

    assert "Math.min(Number(input.max_leads || 20), 20)" in normalize
    assert "outreach_approval: false" in normalize
    assert "Starterangebot" in normalize
    assert sheets["type"] == "n8n-nodes-base.googleSheets"
    assert sheets["parameters"]["sheetName"]["value"] == "Aktivitäten"
    assert workflow["name"] == "Mission Control – Business Automation"
    assert "Approve & Materialize Tasks" not in nodes
    assert nodes["Create Gmail Draft"]["type"] == "n8n-nodes-base.gmail"
    assert nodes["Project Delivery Webhook"]["type"] == "n8n-nodes-base.webhook"
    assert workflow["connections"]["Requirements Complete?"]["main"][0][0]["node"] == "Log Mission in Google Sheets CRM"
    assert workflow["connections"]["Log Mission in Google Sheets CRM"]["main"][0][
        0
    ]["node"] == "Return Mission Started"
    assert workflow["connections"]["Return Mission Started"]["main"][0][0][
        "node"
    ] == "Research Leads & Create Drafts"
    response_body = nodes["Return Mission Started"]["parameters"]["responseBody"]
    assert "status: 'project_created'" in response_body
    assert "research_status: 'queued'" in response_body


def test_business_workflow_reuses_project_drive_hierarchy_and_routes_files():
    workflow_path = (
        Path(__file__).resolve().parents[2]
        / "n8n"
        / "workflows"
        / "mission-control-business-automation.json"
    )
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    nodes = {node["name"]: node for node in workflow["nodes"]}

    for folder in ("Project", "CRM & Leads", "Websites & Angebote", "Berichte & Ergebnisse"):
        assert nodes[f"Search {folder} Folder"]["type"] == "n8n-nodes-base.googleDrive"
        assert nodes[f"Create {folder} Folder"]["type"] == "n8n-nodes-base.googleDrive"
    assert nodes["Copy CRM Sheet to Project"]["parameters"]["operation"] == "copy"
    assert nodes["Copy CRM Sheet to Project"]["parameters"]["folderId"]["value"] == "={{ $json.folders.crm }}"
    assert nodes["Upload Routed Artifacts"]["parameters"][
        "inputDataFieldName"
    ] == "data"
    assert nodes["Log Delivery in Google Sheets"]["parameters"]["sheetName"][
        "value"
    ] == "Aktivitäten"
    assert workflow["connections"]["Log Delivery in Google Sheets"]["main"][0][0]["node"] == "Return Delivery Result"


def test_project_portfolio_persists_tasks_and_agent_assignments(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(run_service, "start", lambda run_id: None)
    with TestClient(app) as client:
        project_response = client.post(
            "/api/v1/projects",
            json={
                "name": "Websites für lokale Unternehmen",
                "goal": "Ein wiederholbares Verkaufs- und Liefermodell aufbauen",
                "category": "business",
                "status": "planning",
                "workspace": str(tmp_path),
                "owner_agent": "boss",
                "deadline": "2026-08-31T18:00:00Z",
                "budget_cents": 25000,
                "revenue_target_cents": 50000,
            },
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        task_response = client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": "Angebot und Zielgruppe recherchieren",
                "task_type": "research",
                "priority": 1,
                "assigned_agent": "atlas",
            },
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]

        projects = client.get("/api/v1/projects")
        assert projects.status_code == 200
        project = projects.json()[0]
        assert project["task_counts"] == {"backlog": 1}
        assert project["owner_agent"] == "boss"
        assert project["budget_cents"] == 25000
        assert project["revenue_target_cents"] == 50000
        assert project["deadline"].startswith("2026-08-31")
        assert project["tasks"][0]["assigned_agent"] == "atlas"
        assert project["tasks"][0]["executable"] is True

        updated = client.patch(
            f"/api/v1/project-tasks/{task_id}",
            json={"status": "in_progress"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "in_progress"

        started = client.post(f"/api/v1/project-tasks/{task_id}/run", json={})
        assert started.status_code == 202
        assert started.json()["run"]["run_kind"] == "task:research"
        assert started.json()["task"]["run_id"] == started.json()["run"]["id"]


def test_coding_project_task_starts_run_and_tracks_completion(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(run_service, "start", lambda run_id: None)
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "Mission Control", "workspace": str(tmp_path)},
        ).json()
        task = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={
                "title": "Health-Endpunkt erweitern",
                "task_type": "coding",
                "assigned_agent": "forge",
            },
        ).json()
        started = client.post(f"/api/v1/project-tasks/{task['id']}/run", json={})
        assert started.status_code == 202
        run_id = started.json()["run"]["id"]
        assert started.json()["task"]["run_id"] == run_id
        assert started.json()["run"]["workstream"] == "project"

        run_service.transition(run_id, "completed")
        refreshed = client.get(f"/api/v1/projects/{project['id']}").json()
        assert refreshed["progress"] == 100
        assert refreshed["tasks"][0]["status"] == "completed"


def test_completed_project_files_are_archived_and_previewed(
    tmp_path: Path, monkeypatch
):
    workspace = tmp_path / "workspace"
    website = workspace / "projects" / "demo"
    website.mkdir(parents=True)
    (website / "index.html").write_text(
        '<!doctype html><link rel="stylesheet" href="style.css"><h1>Demo</h1>',
        encoding="utf-8",
    )
    (website / "style.css").write_text("h1 { color: teal; }", encoding="utf-8")
    monkeypatch.setenv("MISSION_CONTROL_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.delenv("N8N_PROJECT_DELIVERY_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(run_service, "start", lambda run_id: None)

    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "Website Demo", "workspace": str(workspace)},
        ).json()
        task = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={
                "title": "Website-Entwurf bauen",
                "task_type": "coding",
                "assigned_agent": "forge",
            },
        ).json()
        started = client.post(f"/api/v1/project-tasks/{task['id']}/run", json={})
        run_id = started.json()["run"]["id"]
        run_service.update(
            run_id,
            result={
                "summary": "Lieferbarer Website-Entwurf erstellt.",
                "files": [
                    "projects/demo/index.html",
                    "projects/demo/style.css",
                ],
            },
        )
        run_service.transition(run_id, "completed")

        refreshed = client.get(f"/api/v1/projects/{project['id']}")
        assert refreshed.status_code == 200
        artifacts = refreshed.json()["artifacts"]
        website_artifact = next(item for item in artifacts if item["artifact_type"] == "website")
        report = next(item for item in artifacts if item["artifact_type"] == "report")
        assert website_artifact["preview_available"] is True
        assert report["preview_available"] is True
        assert len(artifacts) == 4

        preview = client.get(
            f"/api/v1/project-artifacts/{website_artifact['id']}/preview"
        )
        assert preview.status_code == 200
        assert "Demo" in preview.text
        assert "connect-src 'none'" in preview.headers["content-security-policy"]
        assert "http://127.0.0.1:5173" in preview.headers["content-security-policy"]
        stylesheet = client.get(
            f"/api/v1/project-artifacts/{website_artifact['id']}/preview/style.css"
        )
        assert stylesheet.status_code == 200
        assert "color: teal" in stylesheet.text

        download = client.get(f"/api/v1/project-artifacts/{report['id']}/content")
        assert download.status_code == 200
        assert download.json()["project"]["id"] == project["id"]

        report_preview = client.get(f"/api/v1/project-artifacts/{report['id']}/preview")
        assert report_preview.status_code == 200
        assert report_preview.json()["project"]["id"] == project["id"]

        sync = client.post(f"/api/v1/projects/{project['id']}/artifacts/sync")
        assert sync.status_code == 202
        assert sync.json()["status"] == "unchanged"


def test_project_can_be_archived_and_restored_with_active_run_cancelled(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(run_service, "start", lambda run_id: None)
    with TestClient(app) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "Fehlerhaftes Projekt", "workspace": str(tmp_path)},
        ).json()
        task = client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={
                "title": "Fehler analysieren",
                "task_type": "coding",
                "assigned_agent": "forge",
            },
        ).json()
        started = client.post(f"/api/v1/project-tasks/{task['id']}/run", json={})
        run_id = started.json()["run"]["id"]

        archived = client.post(f"/api/v1/projects/{project['id']}/archive")
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert archived.json()["autopilot_enabled"] is False
        assert archived.json()["tasks"][0]["status"] == "cancelled"
        cancelled_run = run_service.get(run_id)
        assert cancelled_run is not None
        assert cancelled_run["cancel_requested"] is True

        restored = client.post(f"/api/v1/projects/{project['id']}/restore")
        assert restored.status_code == 200
        assert restored.json()["status"] == "paused"


def test_workspace_rejects_parent_and_symlink_escape(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(WorkspaceViolation):
        resolve_workspace_path(workspace, "../outside.txt")

    link = workspace / "link.txt"
    link.symlink_to(outside)
    with pytest.raises(WorkspaceViolation):
        resolve_workspace_path(workspace, "link.txt")


def test_health_exposes_current_mission_control_version():
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        root = client.get("/")
        openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json()["version"] == MISSION_CONTROL_VERSION
    assert root.json()["version"] == MISSION_CONTROL_VERSION
    assert openapi.json()["info"]["version"] == MISSION_CONTROL_VERSION


def test_structured_coder_output():
    result = _parse_output(
        '```json\n{"summary":"ok","edits":[{"path":"a.py","search":"x = 1","replacement":"x = 2"}]}\n```'
    )
    assert result.summary == "ok"
    assert result.edits[0].path == "a.py"
    assert result.edits[0].occurrence is None

    extracted = _parse_output(
        'Ergebnis:\n{"summary":"site","files":[{"path":"projects/demo/index.html","content":"<h1>Demo</h1>"}]}\nFertig.'
    )
    assert extracted.files[0].path == "projects/demo/index.html"

    with pytest.raises(ValueError):
        _parse_output("not-json")


def test_planner_uses_isolated_product_directory_for_new_website(tmp_path: Path):
    plan = create_execution_plan(
        "Projekt: Websites Heidelberg\nAufgabe: Lieferbaren Website-Prototyp bauen",
        workspace=str(tmp_path),
    )

    assert plan.creation_mode is True
    assert plan.output_directory == "projects/websites-heidelberg"
    assert plan.expected_files == []


def test_file_selector_understands_compound_root_endpoint_task(tmp_path: Path):
    backend = tmp_path / "backend" / "app"
    tests = tmp_path / "backend" / "tests"
    backend.mkdir(parents=True)
    tests.mkdir(parents=True)
    (backend / "main.py").write_text(
        '@app.get("/")\ndef root():\n    return {"status": "running"}\n',
        encoding="utf-8",
    )
    (backend / "unrelated.py").write_text("def helper():\n    pass\n", encoding="utf-8")
    (tests / "test_main.py").write_text(
        "def test_root():\n    pass\n", encoding="utf-8"
    )

    selected = select_relevant_files(
        "Ergänze den Root-Endpunkt und füge einen automatisierten Test hinzu",
        workspace=str(tmp_path),
    )

    assert selected[0] == "backend/app/main.py"
    assert "backend/tests/test_main.py" in selected


def test_reviewer_rejects_duplicate_statements(tmp_path: Path):
    target = tmp_path / "test_example.py"
    target.write_text(
        "def test_value():\n"
        "    with client():\n"
        "        value = 1\n"
        "    with client():\n"
        "        value = 1\n",
        encoding="utf-8",
    )

    review = review_changes(str(tmp_path), ["test_example.py"])

    assert review["approved"] is False
    assert "Doppeltes Statement" in review["issues"][0]


def test_run_service_persists_events_and_report(tmp_path: Path):
    run = run_service.create(
        task="Create a safe file",
        workspace=str(tmp_path),
        start=False,
    )
    run_service.transition(run["id"], "planning", "planner")
    run_service.add_event(run["id"], "tool.completed", {"api_key": "hidden"})

    events = run_service.events(run["id"])
    assert events[-1]["payload"]["api_key"] == "[REDACTED]"
    assert "Create a safe file" in (run_service.report(run["id"]) or "")

    with pytest.raises(ValueError, match="bereits"):
        run_service.create(task="Second run", workspace=str(tmp_path), start=False)


def test_failed_run_can_be_resumed(tmp_path: Path, monkeypatch):
    run = run_service.create(task="Resume me", workspace=str(tmp_path), start=False)
    run_service.transition(run["id"], "failed")
    run_service.save_checkpoint(run["id"], {"phase": "broken"})
    monkeypatch.setattr(run_service, "start", lambda run_id: None)

    resumed = run_service.resume(run["id"])

    assert resumed is not None
    assert resumed["status"] == "queued"
    assert resumed["cancel_requested"] is False
    assert run_service.load_checkpoint(run["id"]) == {}


def test_run_api_contract_and_file_boundary(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_service, "start", lambda run_id: None)
    (tmp_path / "inside.txt").write_text("ok", encoding="utf-8")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs",
            json={"task": "Inspect the project", "workspace": str(tmp_path)},
        )
        assert response.status_code == 202
        run_id = response.json()["id"]
        assert client.get(f"/api/v1/runs/{run_id}").status_code == 200
        assert client.get("/api/v1/config").json()["model"] == "qwen2.5:7b"
        assert (
            client.get("/api/v1/config").json()["defaults"]["max_repair_attempts"]
            == 5
        )
        assert client.get(f"/api/v1/runs/{run_id}/diff").status_code == 409
        agents = client.get(f"/api/v1/runs/{run_id}/agents")
        assert agents.status_code == 200
        assert [agent["id"] for agent in agents.json()] == [
            "boss",
            "forge",
            "aura",
            "sage",
            "atlas",
            "flow",
            "orbit",
            "sentinel",
            "mercury",
            "forge_planner",
            "forge_builder",
            "forge_reviewer",
            "forge_publisher",
        ]
        legacy_coder = client.get("/api/v1/agents/coder")
        assert legacy_coder.status_code == 200
        assert legacy_coder.json()["id"] == "forge_builder"
        statuses = client.get("/api/v1/agent-statuses")
        assert statuses.status_code == 200
        assert {status["id"] for status in statuses.json()} >= {
            "offline",
            "active",
            "waiting",
            "blocked",
            "paused",
            "error",
        }
        memory = client.post(
            "/api/v1/agents/boss/memory",
            json={"content": "API zuerst absichern", "kind": "decision", "run_id": run_id},
        )
        assert memory.status_code == 201
        assert client.get(
            "/api/v1/agents/boss/memory", params={"run_id": run_id}
        ).json()[0]["kind"] == "decision"
        delegation = client.post(
            f"/api/v1/runs/{run_id}/delegations",
            json={
                "from_agent": "boss",
                "to_agent": "forge",
                "task": "Technische Umsetzung koordinieren",
            },
        )
        assert delegation.status_code == 201
        assert client.get(f"/api/v1/runs/{run_id}/delegations").json()[0][
            "to_agent"
        ] == "forge"
        assert client.get(f"/api/v1/runs/{run_id}/events").status_code == 200
        assert (
            client.get(
                f"/api/v1/runs/{run_id}/files/content",
                params={"path": "inside.txt"},
            ).json()["content"]
            == "ok"
        )
        escaped = client.get(
            f"/api/v1/runs/{run_id}/files/content",
            params={"path": "../outside.txt"},
        )
        assert escaped.status_code == 403
        assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 200
        report = client.get(f"/api/v1/runs/{run_id}/report")
        assert report.status_code == 200
        assert report.headers["content-type"].startswith("text/markdown")


def test_agent_roster_maps_runtime_steps_to_canonical_roles():
    roster = agent_roster(
        {
            "current_step": "validator",
            "status": "validating",
            "publish": False,
        }
    )

    assert [agent["status"] for agent in roster] == [
        "completed",
        "active",
        "offline",
        "offline",
        "offline",
        "offline",
        "offline",
        "offline",
        "offline",
        "completed",
        "completed",
        "active",
        "waiting",
    ]

    assert next(agent for agent in roster if agent["id"] == "forge_builder")[
        "legacy_ids"
    ] == ["coder", "builder"]

    failed = agent_roster(
        {"current_step": "coder", "status": "failed", "publish": False}
    )
    assert next(agent for agent in failed if agent["id"] == "forge")[
        "status"
    ] == "error"
    assert next(agent for agent in failed if agent["id"] == "forge_builder")[
        "status"
    ] == "error"


def test_agent_memory_and_hierarchical_delegation_are_persistent(tmp_path: Path):
    run = run_service.create(task="Build feature", workspace=str(tmp_path), start=False)

    memory = agent_team.remember(
        "boss", "Priorität: sichere API", kind="decision", run_id=run["id"]
    )
    route = agent_team.handoff(
        run["id"], "boss", "forge_builder", "Implementiere die API"
    )

    assert memory["agent_id"] == "boss"
    assert agent_team.memory("boss", run_id=run["id"])[0]["kind"] == "decision"
    assert [(item["from_agent"], item["to_agent"]) for item in route] == [
        ("boss", "forge"),
        ("forge", "forge_builder"),
    ]


def test_completed_run_changes_can_be_previewed_and_applied_safely(tmp_path: Path):
    source = tmp_path / "source"
    sandbox = tmp_path / "sandbox"
    source.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@mission-control.local"],
        cwd=source,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Mission Control Tests"],
        cwd=source,
        check=True,
    )
    target = source / "value.txt"
    target.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "value.txt"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=source, check=True)
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", "test-run", str(sandbox)],
        cwd=source,
        check=True,
    )
    (sandbox / "value.txt").write_text("after\n", encoding="utf-8")
    (sandbox / ".venv").symlink_to(tmp_path, target_is_directory=True)
    run = {
        "id": "run-1",
        "status": "completed",
        "workspace": str(sandbox),
        "source_workspace": str(source),
    }

    preview = change_service.preview(run)
    assert preview["can_apply"] is True
    assert preview["files"] == ["value.txt"]
    assert preview["untracked_files"] == []

    local_file = source / "local.txt"
    local_file.write_text("user work\n", encoding="utf-8")
    with pytest.raises(ValueError, match="lokale Änderungen"):
        change_service.apply(run)
    local_file.unlink()

    applied = change_service.apply(run)
    assert applied["applied"] is True
    assert len(applied["commit"]) == 40
    assert target.read_text(encoding="utf-8") == "after\n"
    with pytest.raises(RuntimeError):
        change_service.apply(run)


def test_autonomous_engine_completes_with_mocked_model(tmp_path: Path, monkeypatch):
    (tmp_path / "generated.txt").write_text("hello", encoding="utf-8")
    run = run_service.create(
        task="Add a generated file",
        workspace=str(tmp_path),
        start=False,
    )
    monkeypatch.setattr(
        run_engine_module,
        "execute_plan",
        lambda plan, workspace, feedback, blueprint=None: {
            "status": "completed",
            "summary": "done",
            "edits": [
                {
                    "path": "generated.txt",
                    "search": "hello",
                    "replacement": "hello world",
                }
            ],
        },
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_project",
        lambda workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_product_quality",
        lambda plan, workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_product_build",
        lambda plan, workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "review_changes",
        lambda workspace, paths: {"approved": True, "issues": []},
    )

    run_engine_module.run_engine.execute(run["id"])

    completed = run_service.get(run["id"])
    assert completed is not None
    assert completed["status"] == "completed"
    sandbox_file = Path(completed["workspace"]) / "generated.txt"
    assert sandbox_file.read_text(encoding="utf-8") == "hello world"
    assert (tmp_path / "generated.txt").read_text(encoding="utf-8") == "hello"
    assert completed["result"]["files"] == ["generated.txt"]
    assert completed["result"]["blueprint"]["artifact_type"] == "technical_blueprint"
    assert completed["result"]["release_candidate"]["status"] == "ready"
    event_types = {event["type"] for event in run_service.events(run["id"])}
    assert "blueprint.created" in event_types
    assert "release_candidate.created" in event_types
    agent_events = [
        event for event in run_service.events(run["id"]) if event["type"].startswith("agent.")
    ]
    assert any(
        event["type"] == "agent.handoff"
        and event["payload"] == {"from": "boss", "to": "forge_planner"}
        for event in agent_events
    )
    assert agent_events[-1]["payload"] == {"agent": "forge_publisher"}
    assert all(
        delegation["status"] == "completed"
        for delegation in agent_team.delegations(run["id"])
    )


def test_creation_mode_converts_new_file_edit_into_file(tmp_path: Path, monkeypatch):
    run = run_service.create(
        task="Create a website prototype",
        workspace=str(tmp_path),
        start=False,
    )
    plan = ExecutionPlan(
        goal="Create a demo website",
        summary="Build the initial product files",
        creation_mode=True,
        output_directory="projects/demo",
        steps=[
            PlanStep(
                id=1,
                title="Build prototype",
                description="Create the initial HTML file",
                agent="coder",
            )
        ],
    )
    monkeypatch.setattr(
        run_engine_module,
        "create_execution_plan",
        lambda task, workspace: plan,
    )
    monkeypatch.setattr(
        run_engine_module,
        "execute_plan",
        lambda plan, workspace, feedback, blueprint=None: {
            "status": "completed",
            "summary": "created",
            "files": [],
            "edits": [
                {
                    "path": "projects/demo/src/BrandMark.tsx",
                    "search": "missing file",
                    "replacement": "export const BrandMark = () => <strong>Demo</strong>",
                }
            ],
        },
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_project",
        lambda workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_product_quality",
        lambda plan, workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_product_build",
        lambda plan, workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "review_changes",
        lambda workspace, paths: {"approved": True, "issues": []},
    )

    run_engine_module.run_engine.execute(run["id"])

    completed = run_service.get(run["id"])
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["repair_attempts"] == 0
    generated = Path(completed["workspace"]) / "projects/demo/src/BrandMark.tsx"
    assert generated.read_text(encoding="utf-8") == (
        "export const BrandMark = () => <strong>Demo</strong>"
    )
    assert "projects/demo/src/BrandMark.tsx" in completed["result"]["files"]
    assert "projects/demo/package.json" in completed["result"]["files"]
    event_types = {event["type"] for event in run_service.events(run["id"])}
    assert "product.scaffold.created" in event_types


def test_creation_mode_protects_deterministic_scaffold_files(tmp_path: Path):
    plan = ExecutionPlan(
        goal="Create a demo website",
        summary="Build product",
        creation_mode=True,
        output_directory="projects/demo",
        steps=[],
    )

    with pytest.raises(ValueError, match="deterministischen Startergerüst"):
        run_engine_module.run_engine._creation_files(
            plan,
            str(tmp_path),
            {
                "files": [
                    {"path": "projects/demo/package.json", "content": "{}"}
                ],
                "edits": [],
            },
        )

    with pytest.raises(ValueError, match="deterministischen Startergerüst"):
        run_engine_module.run_engine._creation_files(
            plan,
            str(tmp_path),
            {
                "files": [
                    {"path": "projects/demo/src/App.tsx", "content": "bad"}
                ],
                "edits": [],
            },
        )


def test_creation_mode_ignores_redundant_edit_after_full_file_replacement(
    tmp_path: Path,
):
    plan = ExecutionPlan(
        goal="Create a demo website",
        summary="Build product",
        creation_mode=True,
        output_directory="projects/demo",
        steps=[],
    )
    app = tmp_path / "projects/demo/src/content.ts"
    app.parent.mkdir(parents=True)
    app.write_text("old", encoding="utf-8")
    coder_result = {
        "files": [{"path": "projects/demo/src/content.ts", "content": "new"}],
        "edits": [
            {
                "path": "projects/demo/src/content.ts",
                "search": "model hallucinated search",
                "replacement": "ignored",
            }
        ],
    }

    assert run_engine_module.run_engine._creation_edits(
        plan, str(tmp_path), coder_result
    ) == []

    unrelated_edit = {
        "files": [{"path": "projects/demo/src/content.ts", "content": "new"}],
        "edits": [
            {
                "path": "projects/demo/src/theme.css",
                "search": "model hallucinated search",
                "replacement": "ignored in full replacement mode",
            }
        ],
    }
    assert run_engine_module.run_engine._creation_edits(
        plan,
        str(tmp_path),
        unrelated_edit,
        full_replacement=True,
    ) == []


def test_creation_mode_applies_repair_edits_before_full_validation(
    tmp_path: Path, monkeypatch
):
    run = run_service.create(
        task="Create and repair a website prototype",
        workspace=str(tmp_path),
        max_repair_attempts=2,
        start=False,
    )
    plan = ExecutionPlan(
        goal="Create a demo website",
        summary="Build product",
        creation_mode=True,
        output_directory="projects/demo",
        steps=[],
    )
    monkeypatch.setattr(
        run_engine_module, "create_execution_plan", lambda task, workspace: plan
    )
    calls = {"generate": 0, "repository": 0}

    def generate(plan, workspace, feedback, blueprint=None):
        calls["generate"] += 1
        if calls["generate"] == 1:
            return {
                "status": "completed",
                "summary": "initial",
                "files": [
                    {
                        "path": "projects/demo/src/theme.css",
                        "content": "body { color: black; }",
                    }
                ],
            }
        assert "product-reduced-motion" in feedback
        assert "pytest" not in feedback
        return {
            "status": "completed",
            "summary": "repaired",
            "edits": [
                {
                    "path": "projects/demo/src/theme.css",
                    "search": "body { color: black; }",
                    "replacement": (
                        "body { color: black; }\n"
                        "@media (prefers-reduced-motion: reduce) { * { animation: none; } }"
                    ),
                }
            ],
        }

    def product_quality(plan, workspace):
        css = Path(workspace, "projects/demo/src/theme.css").read_text(
            encoding="utf-8"
        )
        success = "prefers-reduced-motion" in css
        return {
            "success": success,
            "checks": [
                {
                    "name": "product-reduced-motion",
                    "success": success,
                    "output": "Reduced motion fehlt" if not success else "OK",
                    "failure_class": None if success else "code",
                }
            ],
        }

    def repository_validation(workspace):
        calls["repository"] += 1
        return {"success": True, "checks": []}

    monkeypatch.setattr(run_engine_module, "execute_plan", generate)
    monkeypatch.setattr(run_engine_module, "validate_product_quality", product_quality)
    monkeypatch.setattr(
        run_engine_module,
        "validate_product_build",
        lambda plan, workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(run_engine_module, "validate_project", repository_validation)
    monkeypatch.setattr(
        run_engine_module,
        "review_changes",
        lambda workspace, paths: {"approved": True, "issues": []},
    )

    run_engine_module.run_engine.execute(run["id"])

    completed = run_service.get(run["id"])
    assert completed is not None and completed["status"] == "completed"
    assert completed["repair_attempts"] == 1
    assert calls == {"generate": 2, "repository": 1}
    repaired = Path(completed["workspace"], "projects/demo/src/theme.css")
    assert "prefers-reduced-motion" in repaired.read_text(encoding="utf-8")


def test_patch_failure_keeps_last_gate_feedback_for_full_replacement(
    tmp_path: Path, monkeypatch
):
    run = run_service.create(
        task="Repair a generated website safely",
        workspace=str(tmp_path),
        max_repair_attempts=3,
        start=False,
    )
    plan = ExecutionPlan(
        goal="Create a demo website",
        summary="Build product",
        creation_mode=True,
        output_directory="projects/demo",
        steps=[],
    )
    monkeypatch.setattr(
        run_engine_module, "create_execution_plan", lambda task, workspace: plan
    )
    calls = {"generate": 0}

    def generate(plan, workspace, feedback, blueprint=None):
        calls["generate"] += 1
        path = "projects/demo/src/theme.css"
        if calls["generate"] == 1:
            return {
                "status": "completed",
                "summary": "initial",
                "files": [{"path": path, "content": "body { color: black; }"}],
            }
        if calls["generate"] == 2:
            assert "product-reduced-motion" in feedback
            return {
                "status": "completed",
                "summary": "ambiguous repair",
                "edits": [
                    {"path": path, "search": "missing", "replacement": "fixed"}
                ],
            }
        assert "patch-application" in feedback
        assert "product-reduced-motion" in feedback
        assert "STRATEGIEWECHSEL" in feedback
        return {
            "status": "completed",
            "summary": "full replacement",
            "files": [
                {
                    "path": path,
                    "content": (
                        "body { color: black; }\n"
                        "@media (prefers-reduced-motion: reduce) { * { animation: none; } }"
                    ),
                }
            ],
        }

    def product_quality(plan, workspace):
        css = Path(workspace, "projects/demo/src/theme.css").read_text(
            encoding="utf-8"
        )
        success = "prefers-reduced-motion" in css
        return {
            "success": success,
            "checks": [
                {
                    "name": "product-reduced-motion",
                    "success": success,
                    "output": "Reduced motion fehlt" if not success else "OK",
                    "failure_class": None if success else "code",
                }
            ],
        }

    monkeypatch.setattr(run_engine_module, "execute_plan", generate)
    monkeypatch.setattr(run_engine_module, "validate_product_quality", product_quality)
    monkeypatch.setattr(
        run_engine_module,
        "validate_product_build",
        lambda plan, workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_project",
        lambda workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "review_changes",
        lambda workspace, paths: {"approved": True, "issues": []},
    )

    run_engine_module.run_engine.execute(run["id"])

    completed = run_service.get(run["id"])
    assert completed is not None and completed["status"] == "completed"
    assert completed["repair_attempts"] == 2
    assert calls["generate"] == 3
    assert any(
        event["type"] == "repair.strategy_changed"
        for event in run_service.events(run["id"])
    )


def test_validator_resolves_homebrew_npm_for_autostart_processes(
    tmp_path: Path, monkeypatch
):
    homebrew = tmp_path / "homebrew"
    homebrew.mkdir()
    npm = homebrew / "npm"
    npm.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(validator_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        validator_module,
        "Path",
        lambda value: homebrew if value == "/opt/homebrew/bin" else Path(value),
    )

    assert validator_module.resolve_executable("npm") == str(npm)


def test_engine_does_not_spend_repairs_on_validation_infrastructure(
    tmp_path: Path, monkeypatch
):
    target = tmp_path / "existing.txt"
    target.write_text("original", encoding="utf-8")
    run = run_service.create(
        task="Validate without npm",
        workspace=str(tmp_path),
        max_repair_attempts=5,
        start=False,
    )
    monkeypatch.setattr(
        run_engine_module,
        "execute_plan",
        lambda plan, workspace, feedback, blueprint=None: {
            "status": "completed",
            "summary": "changed",
            "files": [{"path": "existing.txt", "content": "changed"}],
        },
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_project",
        lambda workspace: {
            "success": False,
            "checks": [
                {
                    "name": "frontend-build",
                    "success": False,
                    "output": "npm missing",
                    "failure_class": "infrastructure",
                }
            ],
        },
    )

    run_engine_module.run_engine.execute(run["id"])

    failed = run_service.get(run["id"])
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["repair_attempts"] == 0
    assert "Validierungsinfrastruktur" in failed["error"]
    assert target.read_text(encoding="utf-8") == "original"


def test_engine_rolls_back_after_validation_failure(tmp_path: Path, monkeypatch):
    target = tmp_path / "existing.txt"
    target.write_text("original", encoding="utf-8")
    run = run_service.create(
        task="Break and repair",
        workspace=str(tmp_path),
        max_repair_attempts=0,
        start=False,
    )
    monkeypatch.setattr(
        run_engine_module,
        "execute_plan",
        lambda plan, workspace, feedback, blueprint=None: {
            "status": "completed",
            "summary": "bad",
            "files": [{"path": "existing.txt", "content": "broken"}],
        },
    )
    monkeypatch.setattr(
        run_engine_module,
        "validate_project",
        lambda workspace: {
            "success": False,
            "checks": [{"name": "test", "success": False}],
        },
    )

    run_engine_module.run_engine.execute(run["id"])

    failed = run_service.get(run["id"])
    assert failed is not None and failed["status"] == "failed"
    assert target.read_text(encoding="utf-8") == "original"


def test_engine_retries_ambiguous_patch(tmp_path: Path, monkeypatch):
    target = tmp_path / "value.py"
    target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    run = run_service.create(
        task="Update one value",
        workspace=str(tmp_path),
        max_repair_attempts=1,
        start=False,
    )
    calls = {"count": 0}

    def generate(plan, workspace, feedback, blueprint=None):
        calls["count"] += 1
        search = "value = 1" if calls["count"] == 1 else "value = 1\nvalue = 1"
        return {
            "status": "completed",
            "summary": "updated",
            "edits": [
                {
                    "path": "value.py",
                    "search": search,
                    "replacement": "value = 2\nvalue = 1",
                }
            ],
        }

    monkeypatch.setattr(run_engine_module, "execute_plan", generate)
    monkeypatch.setattr(
        run_engine_module,
        "validate_project",
        lambda workspace: {"success": True, "checks": []},
    )
    monkeypatch.setattr(
        run_engine_module,
        "review_changes",
        lambda workspace, paths: {"approved": True, "issues": []},
    )

    run_engine_module.run_engine.execute(run["id"])

    completed = run_service.get(run["id"])
    assert completed is not None and completed["status"] == "completed"
    assert completed["repair_attempts"] == 1
    assert calls["count"] == 2


def test_edit_batch_is_atomic_when_later_edit_is_ambiguous(tmp_path: Path):
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text("item = 1\nitem = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exakt einmal"):
        run_engine_module.run_engine._apply_edits(
            "unused",
            str(tmp_path),
            [
                {
                    "path": "first.py",
                    "search": "value = 1",
                    "replacement": "value = 2",
                },
                {
                    "path": "second.py",
                    "search": "item = 1",
                    "replacement": "item = 2",
                },
            ],
            {},
        )

    assert first.read_text(encoding="utf-8") == "value = 1\n"
    assert second.read_text(encoding="utf-8") == "item = 1\nitem = 1\n"


def test_edit_can_target_an_explicit_duplicate_occurrence(tmp_path: Path):
    target = tmp_path / "values.py"
    target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")
    run = run_service.create(task="Edit duplicate", workspace=str(tmp_path), start=False)

    run_engine_module.run_engine._apply_edits(
        run["id"],
        str(tmp_path),
        [
            {
                "path": "values.py",
                "search": "value = 1",
                "replacement": "value = 2",
                "occurrence": 2,
            }
        ],
        {},
    )

    assert target.read_text(encoding="utf-8") == "value = 1\nvalue = 2\n"


def test_repair_limit_does_not_overcount_attempts(tmp_path: Path):
    run = run_service.create(
        task="Fail safely",
        workspace=str(tmp_path),
        max_repair_attempts=1,
        start=False,
    )
    failure = {"success": False, "checks": []}

    run_engine_module.run_engine._schedule_repair(run["id"], failure)
    with pytest.raises(RuntimeError, match="ausgeschöpft"):
        run_engine_module.run_engine._schedule_repair(run["id"], failure)

    current = run_service.get(run["id"])
    assert current is not None
    assert current["repair_attempts"] == 1
    assert run_service.events(run["id"])[-1]["type"] == "repair.exhausted"


def test_github_publisher_creates_pr_and_enables_auto_merge(
    tmp_path: Path, monkeypatch
):
    calls: list[list[str]] = []

    def fake_run(command: list[str], cwd: Path, timeout: int = 120) -> str:
        calls.append(command)
        if command[:3] == ["git", "branch", "--show-current"]:
            return "main"
        if command[:3] == ["git", "status", "--porcelain"]:
            return " M generated.txt"
        if command[:4] == ["git", "remote", "get-url", "origin"]:
            return "https://github.com/example/repo.git"
        return ""

    monkeypatch.setattr(publisher_module, "_run", fake_run)
    github_calls: list[str] = []

    def fake_github(method: str, url: str, *, token: str, payload: dict) -> dict:
        github_calls.append(url)
        if url.endswith("/pulls"):
            return {
                "html_url": "https://github.com/example/repo/pull/1",
                "node_id": "PR_node",
            }
        return {"data": {"enablePullRequestAutoMerge": {}}}

    monkeypatch.setattr(publisher_module, "_github_request", fake_github)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    result = publisher_module.github_publisher.publish(
        workspace=str(tmp_path),
        run_id="12345678-abcd",
        task="Add report export",
        paths=["generated.txt"],
        validation_summary="all green",
    )

    assert result["pr_url"].endswith("/pull/1")
    assert github_calls[-1] == "https://api.github.com/graphql"
