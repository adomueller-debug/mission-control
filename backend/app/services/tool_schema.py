from __future__ import annotations


TOOL_SCHEMAS = [
    {
        "name": "search_symbols",
        "description": "Sucht Klassen und Funktionen im Projekt.",
        "arguments": {
            "query": "string"
        },
    },
    {
        "name": "read_file",
        "description": "Liest den Inhalt einer Datei.",
        "arguments": {
            "path": "string"
        },
    },
    {
        "name": "write_patch",
        "description": "Erzeugt einen Patch für eine Datei.",
        "arguments": {
            "path": "string",
            "content": "string",
        },
    },

    {
        "name": "validate_project",
        "description": "Prüft das Projekt mit Ruff und MyPy.",
        "arguments": {},
    },

    {
        "name": "finish",
        "description": "Beendet die Aufgabe, wenn genug Informationen vorhanden sind.",
        "arguments": {},
    },
]


def get_tool_schemas() -> list[dict]:
    return TOOL_SCHEMAS
