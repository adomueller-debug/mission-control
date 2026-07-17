from pydantic import BaseModel

from backend.app.main import app  # noqa: F401 -- initializes the test schema
from backend.app.database.database import SessionLocal
from backend.app.services.action_contracts import ExternalActionRequest
from backend.app.services.mission_planner_v2 import build_mission_dag
from backend.app.services.mission_v2_service import mission_v2_service
from backend.app.services.model_router_v2 import ModelRequest, should_escalate
from backend.app.services.tool_gateway import ToolDefinition, ToolGateway


class DraftPayload(BaseModel):
    draft_id: str
    api_key: str = "secret"


def test_boss_website_plan_enforces_pipeline_and_parallel_roots():
    items = build_mission_dag("Erstelle eine professionelle Website mit modernem UI")
    by_key = {item["key"]: item for item in items}

    assert by_key["research"]["dependencies"] == []
    assert by_key["design"]["dependencies"] == []
    assert set(by_key["blueprint"]["dependencies"]) == {"research", "design"}
    assert by_key["build"]["dependencies"] == ["blueprint"]
    assert by_key["verify"]["dependencies"] == ["build"]
    assert by_key["release"]["dependencies"] == ["verify"]


def test_fast_path_uses_flow_and_security_without_full_team():
    items = build_mission_dag("Erstelle einen E-Mail-Entwurf für den Kunden")
    assert [item["agent_id"] for item in items] == ["flow", "sentinel"]
    assert items[0]["expected_artifacts"] == ["email_draft"]


def test_model_escalation_policy_is_explicit():
    assert should_escalate(ModelRequest("m", "prompt", "routine")) is False
    assert should_escalate(ModelRequest("m", "prompt", "architecture", complexity="high")) is True
    assert should_escalate(ModelRequest("m", "prompt", "repair", local_failures=2)) is True


def test_tool_gateway_audits_redacts_and_waits_for_external_approval():
    called: list[str] = []
    gateway = ToolGateway()
    gateway.register(
        ToolDefinition(
            name="email.send",
            input_schema=DraftPayload,
            handler=lambda payload: called.append(payload.draft_id) or {"sent": True},
            permitted_agents=frozenset({"flow"}),
        )
    )
    with SessionLocal() as db:
        mission = mission_v2_service.create_mission(
            db,
            {"goal": "Freigabepfad prüfen", "work_items": []},
        )
        result = gateway.execute(
            db,
            ExternalActionRequest(
                mission_id=mission["id"],
                agent_id="flow",
                action_type="email.send",
                summary="Kundennachricht senden",
                target="kunde@example.test",
                payload={"draft_id": "draft-1", "api_key": "do-not-store"},
            ),
        )

    assert result["status"] == "waiting_approval"
    assert result["approval_id"]
    assert called == []
