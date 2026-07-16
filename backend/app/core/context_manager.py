from backend.app.core.context import AgentContext
from backend.app.core.memory import memory


def build_context(task):
    return AgentContext(
        task_id=str(task.id),
        agent_id=task.agent_id,
        instruction=task.instruction,
        memory=memory.get(task.agent_id),
    )
