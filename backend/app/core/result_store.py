class ResultStore:
    def __init__(self):
        self.results = {}

    def save(self, task_id: str, result):
        self.results[task_id] = result

    def get(self, task_id: str):
        return self.results.get(task_id)


result_store = ResultStore()
