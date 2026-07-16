from pathlib import Path
from uuid import uuid4
import difflib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.workspace_security import resolve_workspace_path

router = APIRouter(prefix="/patches", tags=["Patches"])

ROOT = Path.cwd()
_pending: dict[str, dict[str, str]] = {}


class CreatePatchRequest(BaseModel):
    path: str
    content: str


class ApplyPatchRequest(BaseModel):
    patch_id: str


@router.post("/")
def create_patch(request: CreatePatchRequest):
    try:
        file = resolve_workspace_path(ROOT, request.path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if file.exists() and not file.is_file():
        raise HTTPException(status_code=400, detail="Kein Dateiobjekt")

    old_content = (
        file.read_text(encoding="utf-8")
        if file.exists()
        else ""
    )
    patch_id = f"patch-{uuid4().hex[:12]}"

    _pending[patch_id] = {
        "path": request.path,
        "old_content": old_content,
        "new_content": request.content,
    }

    return {
        "patch_id": patch_id,
        "path": request.path,
        "old_content": old_content,
        "new_content": request.content,
    }


@router.get("/{patch_id}")
def get_patch(patch_id: str):
    patch = _pending.get(patch_id)

    if patch is None:
        raise HTTPException(status_code=404, detail="Patch nicht gefunden")

    return {
        "patch_id": patch_id,
        **patch,
    }


@router.post("/apply")
def apply_patch(request: ApplyPatchRequest):
    patch = _pending.get(request.patch_id)

    if patch is None:
        raise HTTPException(status_code=404, detail="Patch nicht gefunden")

    try:
        file = resolve_workspace_path(ROOT, patch["path"])
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(patch["new_content"], encoding="utf-8")
    del _pending[request.patch_id]

    return {
        "success": True,
        "path": patch["path"],
    }


@router.delete("/{patch_id}")
def reject_patch(patch_id: str):
    if patch_id not in _pending:
        raise HTTPException(status_code=404, detail="Patch nicht gefunden")

    del _pending[patch_id]

    return {"success": True}



@router.get("/{patch_id}/diff")
def get_diff(patch_id: str):
    patch = _pending.get(patch_id)

    if patch is None:
        raise HTTPException(status_code=404, detail="Patch nicht gefunden")

    diff = "\n".join(
        difflib.unified_diff(
            patch["old_content"].splitlines(),
            patch["new_content"].splitlines(),
            fromfile="original",
            tofile="updated",
            lineterm="",
        )
    )

    return {
        "patch_id": patch_id,
        "diff": diff,
    }
