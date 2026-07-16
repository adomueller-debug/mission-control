from queue import PriorityQueue
from dataclasses import dataclass, field


@dataclass(order=True)
class QueueTask:
    priority: int
    task: object = field(compare=False)


class TaskQueue:
    def __init__(self):
        self.queue = PriorityQueue()

    def put(self, task, priority: int = 100):
        self.queue.put(QueueTask(priority, task))

    def get(self):
        return self.queue.get().task

    def empty(self):
        return self.queue.empty()


task_queue = TaskQueue()
