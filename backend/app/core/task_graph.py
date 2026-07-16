from dataclasses import dataclass, field


@dataclass
class TaskNode:
    id: str
    description: str
    status: str = "pending"
    depends_on: list[str] = field(default_factory=list)


class TaskGraph:
    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add(self, node: TaskNode):
        self.nodes[node.id] = node

    def ready(self):
        ready = []

        for node in self.nodes.values():
            if node.status != "pending":
                continue

            if all(self.nodes[d].status == "completed" for d in node.depends_on):
                ready.append(node)

        return ready
