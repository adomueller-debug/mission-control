from backend.app.core.checkpoint_manager import checkpoint_manager


class RecoveryManager:
    def recover(self, task_id: str):
        checkpoint = checkpoint_manager.load(task_id)

        if checkpoint is None:
            return None

        return checkpoint.state


recovery = RecoveryManager()
