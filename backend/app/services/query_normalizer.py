from __future__ import annotations

STOP_WORDS = {
    "analysiere",
    "analysier",
    "erstelle",
    "bearbeite",
    "ändere",
    "update",
    "füge",
    "hinzu",
    "die",
    "das",
    "den",
    "eine",
    "einen",
}


def normalize_query(text: str) -> str:
    words = [
        word
        for word in text.replace("/", " ").split()
        if word.lower() not in STOP_WORDS
    ]

    return " ".join(words).strip()
