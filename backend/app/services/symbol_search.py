from backend.app.indexing.symbol_index import build_symbol_index


def search_symbols(query: str, limit: int = 20):
    query = query.lower()

    results = []

    for symbol in build_symbol_index():
        score = 0

        if query in symbol.name.lower():
            score += 100

        if query in symbol.file.lower():
            score += 40

        if score:
            results.append((score, symbol))

    results.sort(reverse=True, key=lambda x: x[0])

    return [symbol for _, symbol in results[:limit]]
