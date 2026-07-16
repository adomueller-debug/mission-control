from datetime import UTC, datetime


class RuntimeMonitor:
    def __init__(self):
        self.started = datetime.now(UTC)

    def uptime(self):
        return datetime.now(UTC) - self.started


runtime_monitor = RuntimeMonitor()
