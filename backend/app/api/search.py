from dataclasses import asdict

from fastapi import APIRouter

from backend.app.services.symbol_search import search_symbols

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/symbols")
def search(query: str):
    return [asdict(item) for item in search_symbols(query)]
