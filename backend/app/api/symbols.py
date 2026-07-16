from dataclasses import asdict

from fastapi import APIRouter

from backend.app.indexing.symbol_index import build_symbol_index

router = APIRouter(prefix="/symbols", tags=["Symbols"])


@router.get("")
def get_symbols():
    return [asdict(symbol) for symbol in build_symbol_index()]
