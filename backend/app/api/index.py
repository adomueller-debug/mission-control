from dataclasses import asdict
from fastapi import APIRouter

from backend.app.indexing.code_index import build_index

router = APIRouter(prefix="/index", tags=["Index"])


@router.get("")
def get_index():
    return [
        asdict(item)
        for item in build_index()
    ]
