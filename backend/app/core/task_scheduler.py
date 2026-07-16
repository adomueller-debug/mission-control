from backend.app.core.task_queue import task_queue


class TaskScheduler:
    def schedule(self, task, priority: int = 100):
        task_queue.put(task, priority)

    def next(self):
        if task_queue.empty():
            return None

        return task_queue.get()


scheduler = TaskScheduler()
