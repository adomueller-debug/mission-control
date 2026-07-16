from backend.app.agents.registry import registry
from backend.app.core.orchestrator import orchestrator
from backend.app.services.project_analysis_service import project_analysis_service
from backend.app.tools.filesystem import filesystem


class DummyTask:
    id = "demo"
    agent_id = "coder"
    instruction = "Write a safe test file."


def test_pipeline_runs(tmp_path, monkeypatch):
    target = tmp_path / "agent-output.txt"
    monkeypatch.setattr(filesystem, "root", tmp_path)
    planner = registry.get("planner")
    calls = {"count": 0}

    def fake_plan(context):
        calls["count"] += 1

        if calls["count"] > 1:
            return {"actions": []}

        return {
            "actions": [
                {
                    "agent": "coder",
                    "tool": "filesystem",
                    "operation": "write",
                    "arguments": {
                            "path": "agent-output.txt",
                        "content": "OK",
                    },
                }
            ]
        }

    monkeypatch.setattr(planner, "execute", fake_plan)
    monkeypatch.setattr(
        project_analysis_service,
        "analyze",
        lambda instruction: {"instruction": instruction},
    )

    result = orchestrator.execute(DummyTask())

    assert result is not None
    assert target.read_text(encoding="utf-8") == "OK"
