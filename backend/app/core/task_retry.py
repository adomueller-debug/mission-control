class TaskRetry:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def should_retry(self, attempts: int) -> bool:
        return attempts < self.max_retries


task_retry = TaskRetry()
