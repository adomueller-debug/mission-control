from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from backend.app.database.database import SessionLocal
from backend.app.main import app
from backend.app.models.mission_v2 import (
    AgentAssignment,
    Approval,
    AuditedToolCall,
    CostEntry,
    Mission,
    QualityGate,
    ResourceLease,
    WorkItem,
)
from backend.app.services.mission_v2_service import mission_v2_service, utcnow, validate_dag


@pytest.fixture(autouse=True)
def clean_v2_data():
    yield
    with SessionLocal() as db:
        for model in (
            ResourceLease,
            CostEntry,
            Approval,
            QualityGate,
            AuditedToolCall,
            AgentAssignment,
            WorkItem,
            Mission,
        ):
            db.execute(delete(model))
        db.commit()


def _mission_payload() -> dict:
    return {
        "goal": "Eine hochwertige responsive Website entwickeln",
        "budget_cents": 1_500,
        "success_criteria": ["Responsive Preview", "Tests grün"],
        "work_items": [
            {
                "key": "blueprint",
                "title": "Architektur und Designvertrag erstellen",
                "agent_id": "forge_planner",
                "acceptance_criteria": ["Dateiplan vorhanden"],
            },
            {
                "key": "build",
                "title": "Website implementieren",
                "agent_id": "forge_builder",
                "dependencies": ["blueprint"],
                "resource_keys": ["repo:website"],
                "expected_artifacts": ["website-preview"],
            },
        ],
    }


def test_dag_validation_rejects_missing_dependencies_and_cycles():
    with pytest.raises(ValueError, match="Unbekannte Abhängigkeit"):
        validate_dag([{"key": "build", "dependencies": ["blueprint"]}])

    with pytest.raises(ValueError, match="Abhängigkeitszyklus"):
        validate_dag(
            [
                {"key": "a", "dependencies": ["b"]},
                {"key": "b", "dependencies": ["a"]},
            ]
        )


def test_mission_api_persists_dag_assignments_and_real_progress():
    with TestClient(app) as client:
        created_response = client.post("/api/v2/missions", json=_mission_payload())
        assert created_response.status_code == 201
        created = created_response.json()
        assert created["status"] == "ready"
        assert created["progress"]["percent"] == 0
        by_key = {item["key"]: item for item in created["work_items"]}
        assert by_key["blueprint"]["status"] == "ready"
        assert by_key["build"]["status"] == "queued"

        assignments = client.get(
            f"/api/v2/missions/{created['id']}/assignments"
        ).json()
        assert {item["agent_id"] for item in assignments} == {
            "forge_planner",
            "forge_builder",
        }

        completed = client.patch(
            f"/api/v2/work-items/{by_key['blueprint']['id']}/status",
            json={"status": "completed"},
        )
        assert completed.status_code == 200
        refreshed = client.get(f"/api/v2/missions/{created['id']}").json()
        assert refreshed["progress"]["percent"] == 50
        refreshed_by_key = {item["key"]: item for item in refreshed["work_items"]}
        assert refreshed_by_key["build"]["status"] == "ready"
        timeline = client.get(f"/api/v2/missions/{created['id']}/events")
        assert timeline.status_code == 200
        assert len(timeline.json()) == 2


def test_skipped_work_requires_visible_reason():
    with TestClient(app) as client:
        mission = client.post("/api/v2/missions", json=_mission_payload()).json()
        item_id = mission["work_items"][0]["id"]
        invalid = client.patch(
            f"/api/v2/work-items/{item_id}/status", json={"status": "skipped"}
        )
        assert invalid.status_code == 422
        valid = client.patch(
            f"/api/v2/work-items/{item_id}/status",
            json={"status": "skipped", "skip_reason": "Vorhandene Architektur wiederverwendet"},
        )
        assert valid.status_code == 200
        assert valid.json()["skip_reason"] == "Vorhandene Architektur wiederverwendet"


def test_external_action_approval_is_persistent_and_single_decision():
    with TestClient(app) as client:
        mission = client.post("/api/v2/missions", json={"goal": "E-Mail vorbereiten"}).json()
        approval = client.post(
            "/api/v2/approvals",
            json={
                "mission_id": mission["id"],
                "action_type": "email.send",
                "summary": "Angebot an den Kunden senden",
                "target": "kunde@example.test",
                "risk_level": 2,
                "payload_preview": {"subject": "Ihr Website-Angebot"},
            },
        )
        assert approval.status_code == 201
        assert approval.json()["payload_preview"]["subject"] == "Ihr Website-Angebot"
        assert client.get("/api/v2/approvals").json()[0]["status"] == "pending"

        approved = client.post(
            f"/api/v2/approvals/{approval.json()['id']}/approve",
            json={"note": "Inhalt geprüft"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        duplicate = client.post(
            f"/api/v2/approvals/{approval.json()['id']}/approve", json={}
        )
        assert duplicate.status_code == 409


def test_audited_tool_calls_are_idempotent_per_mission_and_tool():
    with SessionLocal() as db:
        mission = mission_v2_service.create_mission(db, {"goal": "Datei analysieren"})
        payload = {
            "mission_id": mission["id"],
            "agent_id": "atlas",
            "tool_name": "document_reader",
            "risk_level": 0,
            "idempotency_key": "document-1",
            "request_redacted": {"path": "[WORKSPACE]/brief.pdf"},
        }
        first = mission_v2_service.record_tool_call(db, payload)
        second = mission_v2_service.record_tool_call(db, payload)
        assert first["id"] == second["id"]
        assert first["request_redacted"] == {"path": "[WORKSPACE]/brief.pdf"}


def test_expired_lease_recovers_assignment_for_retry():
    with SessionLocal() as db:
        mission = mission_v2_service.create_mission(db, _mission_payload())
        item = db.scalar(
            select(WorkItem).where(
                WorkItem.mission_id == mission["id"], WorkItem.key == "blueprint"
            )
        )
        assert item is not None
        assignment = db.scalar(
            select(AgentAssignment).where(AgentAssignment.work_item_id == item.id)
        )
        assert assignment is not None
        item.status = "active"
        assignment.status = "active"
        db.commit()

        assert mission_v2_service.acquire_lease(
            db,
            resource_key="llm:local",
            mission_id=mission["id"],
            work_item_id=item.id,
            assignment_id=assignment.id,
            owner_id="worker-a",
        )
        assert not mission_v2_service.acquire_lease(
            db,
            resource_key="llm:local",
            mission_id=mission["id"],
            work_item_id=item.id,
            assignment_id=assignment.id,
            owner_id="worker-b",
        )
        lease = db.get(ResourceLease, "llm:local")
        assert lease is not None
        lease.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()

        assert mission_v2_service.recover_expired_leases(db) == [item.id]
        db.refresh(item)
        db.refresh(assignment)
        assert item.status == "retrying"
        assert item.attempts == 1
        assert assignment.status == "queued"
        assert db.get(ResourceLease, "llm:local") is None


def test_budget_and_agent_endpoints_reflect_persisted_state():
    with SessionLocal() as db:
        mission = mission_v2_service.create_mission(db, _mission_payload())
        mission_v2_service.add_cost(
            db,
            {
                "mission_id": mission["id"],
                "provider": "openai-compatible",
                "model": "quality-model",
                "estimated_cents": 40,
                "actual_cents": 35,
            },
        )
        assignment = db.scalar(
            select(AgentAssignment).where(AgentAssignment.mission_id == mission["id"])
        )
        assert assignment is not None
        assignment.status = "active"
        db.commit()

    with TestClient(app) as client:
        budget = client.get(
            "/api/v2/budgets", params={"mission_id": mission["id"]}
        ).json()
        assert budget["actual_cents"] == 35
        assert budget["monthly_limit_cents"] == 2_000
        agents = client.get("/api/v2/agents").json()
        blueprint = next(item for item in agents if item["id"] == "forge_planner")
        assert blueprint["status"] == "active"
        assert len(blueprint["active_assignments"]) == 1
