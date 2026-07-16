from backend.app.core.checkpoint import Checkpoint


class CheckpointManager:
    def __init__(self):
        self.checkpoints = {}

    def save(self, task_id: str, state: dict):
        self.checkpoints[task_id] = Checkpoint(task_id, state)

    def load(self, task_id: str):
        return self.checkpoints.get(task_id)


checkpoint_manager = CheckpointManager()
