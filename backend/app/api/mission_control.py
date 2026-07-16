from fastapi import APIRouter

from backend.app.core.agent_state_manager import agent_states
from backend.app.core.runtime_monitor import runtime_monitor
from backend.app.core.runtime_stats import runtime_stats
from backend.app.core.event_logger import event_logger

router = APIRouter(
    prefix="/mission-control",
    tags=["Mission Control"],
)


@router.get("/status")
def status():
    return {
        "uptime": str(runtime_monitor.uptime()),
        "agents": {
            name: {
                "status": state.status,
                "current_task": state.current_task,
                "completed_tasks": state.completed_tasks,
            }
            for name, state in agent_states.states.items()
        },
        "runtime": runtime_stats.all(),
        "events": [
            {
                "agent": e.agent,
                "action": e.action,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in event_logger.all()[-100:]
        ],
    }
