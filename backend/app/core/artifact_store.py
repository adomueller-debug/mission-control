class ArtifactStore:
    def __init__(self):
        self.artifacts = {}

    def save(self, task_id, key, value):
        self.artifacts.setdefault(task_id, {})
        self.artifacts[task_id][key] = value

    def get(self, task_id):
        return self.artifacts.get(task_id, {})


artifact_store = ArtifactStore()
