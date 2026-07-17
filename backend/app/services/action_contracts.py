from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.services.risk_policy import RiskLevel, risk_for


class EmailDraft(BaseModel):
    to: list[str] = Field(min_length=1, max_length=50)
    cc: list[str] = Field(default_factory=list, max_length=50)
    subject: str = Field(min_length=1, max_length=998)
    body_text: str = Field(min_length=1, max_length=100_000)
    attachments: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("to", "cc")
    @classmethod
    def validate_addresses(cls, addresses: list[str]) -> list[str]:
        for address in addresses:
            local, separator, domain = address.strip().rpartition("@")
            if not separator or not local or "." not in domain:
                raise ValueError(f"Ungültige E-Mail-Adresse: {address}")
        return addresses


class CalendarEventDraft(BaseModel):
    calendar_id: str = "primary"
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=20_000)
    location: str = Field(default="", max_length=1_000)
    start_at: datetime
    end_at: datetime
    timezone: str = "Europe/Berlin"
    attendees: list[str] = Field(default_factory=list, max_length=200)
    create_meet: bool = False

    @field_validator("attendees")
    @classmethod
    def validate_attendees(cls, attendees: list[str]) -> list[str]:
        for address in attendees:
            local, separator, domain = address.strip().rpartition("@")
            if not separator or not local or "." not in domain:
                raise ValueError(f"Ungültige E-Mail-Adresse: {address}")
        return attendees

    @model_validator(mode="after")
    def validate_time_range(self) -> "CalendarEventDraft":
        if self.end_at <= self.start_at:
            raise ValueError("Kalendertermin muss nach seinem Beginn enden.")
        return self


class CommerceItem(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=8, max_length=4_000)
    quantity: int = Field(default=1, ge=1, le=100)
    unit_price_cents: int = Field(ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)


class CommerceCartDraft(BaseModel):
    merchant: str = Field(min_length=1, max_length=200)
    items: list[CommerceItem] = Field(min_length=1, max_length=100)
    shipping_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    @property
    def total_cents(self) -> int:
        return self.shipping_cents + sum(
            item.unit_price_cents * item.quantity for item in self.items
        )


class SocialDraft(BaseModel):
    platform: Literal["instagram", "tiktok"]
    asset_paths: list[str] = Field(min_length=1, max_length=20)
    caption: str = Field(min_length=1, max_length=2_200)
    hashtags: list[str] = Field(default_factory=list, max_length=30)
    ai_generated: bool = True
    publish_mode: Literal["draft", "publish"] = "draft"


class ExternalActionRequest(BaseModel):
    mission_id: str
    work_item_id: str | None = None
    agent_id: str
    action_type: str
    summary: str = Field(min_length=2, max_length=2_000)
    target: str = Field(default="", max_length=2_000)
    payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: int | None = Field(default=None, ge=0, le=3)
    idempotency_key: str = ""

    @model_validator(mode="after")
    def derive_policy_fields(self) -> "ExternalActionRequest":
        expected = int(risk_for(self.action_type))
        if self.risk_level is None:
            self.risk_level = expected
        elif self.risk_level < expected:
            raise ValueError("Risikostufe darf die Systemrichtlinie nicht unterschreiten.")
        if not self.idempotency_key:
            stable = json.dumps(
                {
                    "mission_id": self.mission_id,
                    "work_item_id": self.work_item_id,
                    "action_type": self.action_type,
                    "target": self.target,
                    "payload": self.payload,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:32]
            self.idempotency_key = f"{self.mission_id}:{digest}"
        return self

    @property
    def approval_required(self) -> bool:
        return int(self.risk_level or 0) >= int(RiskLevel.APPROVAL)
