from backend.app.core.task_graph import TaskGraph, TaskNode


class Workflow:
    def __init__(self):
        self.graph = TaskGraph()

    def from_plan(self, steps: list[str]):
        previous = None

        for i, step in enumerate(steps):
            node = TaskNode(
                id=f"step_{i}",
                description=step,
                depends_on=[] if previous is None else [previous],
            )

            self.graph.add(node)
            previous = node.id

        return self.graph
