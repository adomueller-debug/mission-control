from datetime import datetime


class Logger:
    @staticmethod
    def info(msg: str):
        print(f"[{datetime.now().isoformat()}] INFO  {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"[{datetime.now().isoformat()}] WARN  {msg}")

    @staticmethod
    def error(msg: str):
        print(f"[{datetime.now().isoformat()}] ERROR {msg}")
