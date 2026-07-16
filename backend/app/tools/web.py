import requests


def execute(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text
