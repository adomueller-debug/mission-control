from __future__ import annotations

from typing import Any

from backend.app.services.symbol_search import search_symbols
from backend.app.tools.base import Tool


class SearchSymbolsTool(Tool):
    name = "search_symbols"
    description = "Sucht Klassen und Funktionen im Projekt."

    def run(self, **kwargs: Any):
        query = kwargs.get("query")

        if not isinstance(query, str) or not query:
            raise ValueError("Parameter 'query' fehlt.")

        limit = kwargs.get("limit", 10)

        return [
            {
                "name": symbol.name,
                "kind": symbol.kind,
                "file": symbol.file,
                "line": symbol.line,
            }
            for symbol in search_symbols(query, limit)
        ]


search_symbols_tool = SearchSymbolsTool()
