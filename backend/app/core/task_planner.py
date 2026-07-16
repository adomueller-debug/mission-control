from backend.app.core.agent_task import AgentTask


class TaskPlanner:
    def build(self, plan):
        tasks = []

        for i, step in enumerate(plan.steps):
            tasks.append(
                AgentTask(
                    id=step.id,
                    instruction=step.description,
                    assigned_agent=step.agent,
                    tool=step.tool,
                )
            )

        return tasks


task_planner = TaskPlanner()
