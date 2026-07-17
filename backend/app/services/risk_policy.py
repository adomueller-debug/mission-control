from __future__ import annotations

from enum import IntEnum


class RiskLevel(IntEnum):
    AUTONOMOUS = 0
    AUDITED = 1
    APPROVAL = 2
    CONFIRMATION = 3


ACTION_RISK_LEVELS: dict[str, RiskLevel] = {
    "research.search": RiskLevel.AUTONOMOUS,
    "filesystem.write_sandbox": RiskLevel.AUTONOMOUS,
    "email.create_draft": RiskLevel.AUTONOMOUS,
    "drive.sync": RiskLevel.AUDITED,
    "crm.update": RiskLevel.AUDITED,
    "git.create_branch": RiskLevel.AUDITED,
    "calendar.prepare_event": RiskLevel.AUTONOMOUS,
    "email.send": RiskLevel.APPROVAL,
    "calendar.create_event": RiskLevel.APPROVAL,
    "calendar.invite_attendees": RiskLevel.APPROVAL,
    "social.upload_draft": RiskLevel.APPROVAL,
    "social.publish": RiskLevel.APPROVAL,
    "github.publish_pr": RiskLevel.APPROVAL,
    "deployment.publish": RiskLevel.APPROVAL,
    "commerce.prepare_cart": RiskLevel.AUDITED,
    "commerce.checkout": RiskLevel.CONFIRMATION,
    "payment.execute": RiskLevel.CONFIRMATION,
    "contract.accept": RiskLevel.CONFIRMATION,
    "external.delete": RiskLevel.CONFIRMATION,
    "permissions.change": RiskLevel.CONFIRMATION,
}


def risk_for(action_type: str) -> RiskLevel:
    return ACTION_RISK_LEVELS.get(action_type, RiskLevel.CONFIRMATION)


def requires_approval(action_type: str) -> bool:
    return risk_for(action_type) >= RiskLevel.APPROVAL


def can_bundle(action_type: str) -> bool:
    return risk_for(action_type) == RiskLevel.APPROVAL

