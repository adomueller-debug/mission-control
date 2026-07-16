from backend.app.runtime.agent_loop import agent_loop
from backend.app.agents.registry import registry
from backend.app.core.context_manager import build_context
from backend.app.services.project_analysis_service import project_analysis_service


class Orchestrator:

    def execute(self, task):
        context = build_context(task)

        planner = registry.get("planner")

        plan = planner.execute(context)

        results = agent_loop.execute(
            planner,
            context,
            initial_plan=plan,
        )

        return {
            "analysis": project_analysis_service.analyze(task.instruction),
            "plan": plan,
            "results": results,
        }


orchestrator = Orchestrator()
