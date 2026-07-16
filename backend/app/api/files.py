from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.workspace_security import resolve_workspace_path

router = APIRouter(prefix="/files", tags=["Files"])

ROOT = Path.cwd()


@router.get("/")
def list_files():
    excluded = {
        ".git",
        ".idea",
        ".venv",
        ".vscode",
        "__pycache__",
        "data",
        "dist",
        "node_modules",
    }

    result = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)

        if any(part in excluded for part in relative.parts):
            continue

        result.append(relative.as_posix())

    result.sort()
    return result


@router.get("/content")
def file_content(path: str):
    try:
        file = resolve_workspace_path(ROOT, path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if not file.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")

    if not file.is_file():
        raise HTTPException(status_code=400, detail="Kein Dateiobjekt")

    return {
        "path": path,
        "content": file.read_text(encoding="utf-8", errors="ignore"),
    }



class SaveFileRequest(BaseModel):
    path: str
    content: str


@router.post("/content")
def save_file(request: SaveFileRequest):
    try:
        file = resolve_workspace_path(ROOT, request.path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if not file.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")

    if not file.is_file():
        raise HTTPException(status_code=400, detail="Kein Dateiobjekt")

    file.write_text(request.content, encoding="utf-8")

    return {"success": True}
