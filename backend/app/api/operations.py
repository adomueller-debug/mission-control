from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.runs import RunOptions
from backend.app.services.operations_router import operations_router


router = APIRouter(prefix="/api/v1", tags=["Operations"])


class OperationIntakeRequest(BaseModel):
    task: str = Field(min_length=3, max_length=20_000)
    workspace: str = Field(default_factory=lambda: str(Path.cwd()))
    options: RunOptions = Field(default_factory=RunOptions)
    answers: dict[str, Any] = Field(default_factory=dict)


@router.post("/operations/intake", status_code=202)
def operation_intake(request: OperationIntakeRequest):
    try:
        return operations_router.intake(
            task=request.task,
            workspace=request.workspace,
            options=request.options.model_dump(),
            answers=request.answers,
        )
    except requests.Timeout as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "n8n hat die Mission angenommen, aber nicht rechtzeitig bestätigt. "
                "Die Verarbeitung kann im Hintergrund weiterlaufen; bitte zuerst das "
                "Projektboard prüfen, bevor du die Mission erneut absendest."
            ),
        ) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail="Der n8n-Business-Workflow ist derzeit nicht erreichbar.",
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
