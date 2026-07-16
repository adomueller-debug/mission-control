from backend.app.core.runtime import runtime


class TaskDispatcher:
    def dispatch(self, context, tasks):
        results = []

        for task in tasks:
            context.variables["current_task"] = task
            result = runtime.run(task.assigned_agent, context)
            task.result = result
            task.status = "completed"
            results.append(task)

        return results


task_dispatcher = TaskDispatcher()
