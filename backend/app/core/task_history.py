from collections import defaultdict


class TaskHistory:
    def __init__(self):
        self.history = defaultdict(list)

    def add(self, task_id: str, item):
        self.history[task_id].append(item)

    def get(self, task_id: str):
        return self.history[task_id]


task_history = TaskHistory()
