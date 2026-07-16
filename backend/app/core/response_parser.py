import json


class ResponseParser:
    @staticmethod
    def parse_json(text: str):
        try:
            return json.loads(text)
        except Exception:
            return {"raw": text}
