class TaskValidator:
    def validate(self, task):
        return bool(task.result)


task_validator = TaskValidator()
