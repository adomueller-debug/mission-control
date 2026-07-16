from backend.app.agents.registry import registry
from backend.app.core.agent_state_manager import agent_states
from backend.app.core.context_manager import build_context
from backend.app.core.event_logger import event_logger
from backend.app.core.runtime_stats import runtime_stats


def _run_agent(name, context, variable):
    state = agent_states.get(name)
    state.status = "running"
    state.current_task = context.instruction

    event_logger.log(name, "started", {"task": context.instruction})
    runtime_stats.increment(f"{name}_started")

    try:
        result = registry.get(name).execute(context)
        context.variables[variable] = result

        state.completed_tasks += 1
        event_logger.log(name, "completed", {"task": context.instruction})
        runtime_stats.increment(f"{name}_completed")

        return result
    except Exception as exc:
        state.status = "failed"
        event_logger.log(name, "failed", {"error": str(exc)})
        runtime_stats.increment(f"{name}_failed")
        raise
    finally:
        if state.status != "failed":
            state.status = "idle"
        state.current_task = None


def coordinate(task):
    context = build_context(task)

    plan = _run_agent("planner", context, "plan")
    implementation = _run_agent("coder", context, "implementation")
    analysis = _run_agent("analyst", context, "analysis")

    return {
        "plan": plan,
        "implementation": implementation,
        "analysis": analysis,
    }
