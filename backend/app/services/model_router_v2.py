from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
import threading
from typing import Literal

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.mission_v2 import CostEntry


LOCAL_LLM_LOCK = threading.Semaphore(1)


class ModelBudgetExceeded(RuntimeError):
    pass


class ModelProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelRequest:
    mission_id: str
    prompt: str
    purpose: str
    complexity: Literal["routine", "high"] = "routine"
    local_failures: int = 0
    repair_failures: int = 0
    customer_quality_gate: bool = False
    assignment_id: str | None = None
    max_output_tokens: int = 4096


@dataclass(frozen=True)
class ModelResponse:
    text: str
    provider: str
    model: str
    escalated: bool
    estimated_cents: int
    actual_cents: int


def should_escalate(request: ModelRequest) -> bool:
    return bool(
        request.complexity == "high"
        or request.local_failures >= 2
        or request.repair_failures >= 2
        or request.customer_quality_gate
    )


class ModelRouterV2:
    """Serializes local inference and enforces a persistent external cost ceiling."""

    def generate(self, db: Session, request: ModelRequest) -> ModelResponse:
        external_available = bool(
            os.getenv("QUALITY_LLM_API_KEY")
            and os.getenv("QUALITY_LLM_BASE_URL")
            and os.getenv("QUALITY_LLM_MODEL")
        )
        if should_escalate(request) and external_available:
            estimate = self._estimate_external_cents(request)
            reservation = self._reserve_budget(db, request, estimate)
            try:
                return self._external(db, request, estimate, reservation)
            except (requests.RequestException, ValueError, KeyError) as exc:
                self._record_failed_reservation(db, reservation)
                # Quality escalation is optional; the local provider remains the safe fallback.
                return self._local(db, request, fallback_reason=str(exc))
        return self._local(db, request)

    def _local(
        self, db: Session, request: ModelRequest, fallback_reason: str = ""
    ) -> ModelResponse:
        url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        with LOCAL_LLM_LOCK:
            try:
                response = requests.post(
                    url,
                    json={
                        "model": model,
                        "prompt": request.prompt,
                        "stream": False,
                        "options": {
                            "num_ctx": int(os.getenv("OLLAMA_CONTEXT", "8192")),
                            "num_predict": request.max_output_tokens,
                        },
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                text = str(response.json()["response"])
            except (requests.RequestException, KeyError, ValueError) as exc:
                suffix = f"; externe Eskalation: {fallback_reason}" if fallback_reason else ""
                raise ModelProviderUnavailable(f"Lokales Modell nicht erreichbar: {exc}{suffix}") from exc
        db.add(
            CostEntry(
                mission_id=request.mission_id,
                assignment_id=request.assignment_id,
                provider="ollama",
                model=model,
                kind=request.purpose,
            )
        )
        db.commit()
        return ModelResponse(text, "ollama", model, False, 0, 0)

    def _external(
        self, db: Session, request: ModelRequest, estimate: int, entry: CostEntry
    ) -> ModelResponse:
        base = os.environ["QUALITY_LLM_BASE_URL"].rstrip("/")
        model = os.environ["QUALITY_LLM_MODEL"]
        response = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['QUALITY_LLM_API_KEY']}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_output_tokens,
            },
            timeout=int(os.getenv("QUALITY_LLM_TIMEOUT", "120")),
        )
        response.raise_for_status()
        payload = response.json()
        text = str(payload["choices"][0]["message"]["content"])
        usage = payload.get("usage", {})
        actual = int(payload.get("cost_cents", estimate))
        entry.provider = "quality"
        entry.actual_cents = actual
        entry.input_tokens = int(usage.get("prompt_tokens", 0))
        entry.output_tokens = int(usage.get("completion_tokens", 0))
        db.commit()
        return ModelResponse(text, "quality", model, True, estimate, actual)

    def _reserve_budget(
        self, db: Session, request: ModelRequest, estimate: int
    ) -> CostEntry:
        limit = int(os.getenv("QUALITY_LLM_MONTHLY_LIMIT_CENTS", "2000"))
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = int(
            db.scalar(
                select(func.coalesce(func.sum(CostEntry.actual_cents), 0)).where(
                    CostEntry.provider == "quality", CostEntry.created_at >= month_start
                )
            )
            or 0
        )
        reserved = int(
            db.scalar(
                select(func.coalesce(func.sum(CostEntry.estimated_cents), 0)).where(
                    CostEntry.provider == "quality-reservation",
                    CostEntry.actual_cents == 0,
                    CostEntry.created_at >= month_start,
                )
            )
            or 0
        )
        if spent + reserved + estimate > limit:
            raise ModelBudgetExceeded(
                f"Externes Monatsbudget von {limit / 100:.2f} € ist ausgeschöpft"
            )
        entry = CostEntry(
            mission_id=request.mission_id,
            assignment_id=request.assignment_id,
            provider="quality-reservation",
            model=os.getenv("QUALITY_LLM_MODEL", ""),
            kind=request.purpose,
            estimated_cents=estimate,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def _record_failed_reservation(
        db: Session, entry: CostEntry
    ) -> None:
        # A failed reservation remains auditable but no longer blocks the budget.
        entry.provider = "quality-failed"
        db.commit()

    @staticmethod
    def _estimate_external_cents(request: ModelRequest) -> int:
        configured = os.getenv("QUALITY_LLM_ESTIMATED_CALL_CENTS")
        if configured:
            return max(1, int(configured))
        prompt_tokens = max(1, len(request.prompt) // 4)
        return max(1, round((prompt_tokens + request.max_output_tokens) * 0.001))


model_router_v2 = ModelRouterV2()
