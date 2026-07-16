class Pipeline:
    def __init__(self):
        self.steps = []

    def add(self, step):
        self.steps.append(step)

    def execute(self, context):
        for step in self.steps:
            step(context)

        return context
