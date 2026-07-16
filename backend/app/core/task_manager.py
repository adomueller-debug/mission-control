from backend.app.core.task_status import TaskStatus


class TaskManager:
    def start(self, task):
        task.status = TaskStatus.RUNNING

    def complete(self, task):
        task.status = TaskStatus.COMPLETED

    def fail(self, task):
        task.status = TaskStatus.FAILED


task_manager = TaskManager()
