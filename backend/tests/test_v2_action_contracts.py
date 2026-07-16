from datetime import UTC, datetime, timedelta

import pytest

from backend.app.services.action_contracts import (
    CalendarEventDraft,
    CommerceCartDraft,
    CommerceItem,
    ExternalActionRequest,
)
from backend.app.services.risk_policy import RiskLevel, can_bundle, risk_for


def test_external_action_derives_stable_idempotency_and_risk():
    payload = {
        "mission_id": "mission-1",
        "agent_id": "flow",
        "action_type": "email.send",
        "summary": "Freigegebene Nachricht versenden",
        "target": "kunde@example.test",
        "payload": {"draft_id": "draft-1"},
    }
    first = ExternalActionRequest(**payload)
    second = ExternalActionRequest(**payload)

    assert first.risk_level == RiskLevel.APPROVAL
    assert first.approval_required is True
    assert first.idempotency_key == second.idempotency_key
    assert can_bundle(first.action_type) is True


def test_unknown_action_defaults_to_individual_confirmation():
    assert risk_for("unknown.external.action") == RiskLevel.CONFIRMATION


def test_risk_cannot_be_downgraded_by_agent():
    with pytest.raises(ValueError, match="Risikostufe"):
        ExternalActionRequest(
            mission_id="mission-1",
            agent_id="boss",
            action_type="commerce.checkout",
            summary="Checkout",
            risk_level=1,
        )


def test_calendar_and_cart_contracts_validate_real_world_constraints():
    start = datetime.now(UTC)
    event = CalendarEventDraft(
        title="Kundentermin",
        start_at=start,
        end_at=start + timedelta(hours=1),
        attendees=["kunde@example.test"],
    )
    cart = CommerceCartDraft(
        merchant="Example Shop",
        items=[
            CommerceItem(
                name="Produkt",
                url="https://example.test/product",
                unit_price_cents=1299,
                quantity=2,
            )
        ],
        shipping_cents=499,
    )

    assert event.attendees == ["kunde@example.test"]
    assert cart.total_cents == 3097
