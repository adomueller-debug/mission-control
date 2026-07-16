from backend.app.agents.coordinator import coordinate


def execute(task):
    return coordinate(task)
