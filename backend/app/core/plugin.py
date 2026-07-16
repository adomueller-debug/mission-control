class Plugin:
    name = "plugin"

    def execute(self, *args, **kwargs):
        raise NotImplementedError
