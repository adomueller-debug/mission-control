from __future__ import annotations

from typing import Any
import os
from pathlib import Path

from dotenv import set_key
from sqlalchemy import select

from backend.app.database.database import SessionLocal
from backend.app.models.mission import IntegrationRequirement
from backend.app.models.project import Project
from backend.app.services.integration_catalog import (
    INTEGRATION_BY_ID,
    integration_catalog,
    integration_status,
)


def requirement_to_dict(requirement: IntegrationRequirement) -> dict[str, Any]:
    integration = integration_status(INTEGRATION_BY_ID[requirement.integration_id])
    return {
        "id": requirement.id,
        "project_id": requirement.project_id,
        "integration_id": requirement.integration_id,
        "purpose": requirement.purpose,
        "required": requirement.required,
        "status": integration["status"],
        "ready": integration["ready"],
        "integration": integration,
        "created_at": requirement.created_at.isoformat(),
    }


class IntegrationService:
    def catalog(self) -> list[dict[str, Any]]:
        return integration_catalog()

    def requirements(self, project_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as db:
            rows = db.scalars(
                select(IntegrationRequirement)
                .where(IntegrationRequirement.project_id == project_id)
                .order_by(IntegrationRequirement.created_at)
            ).all()
            return [requirement_to_dict(row) for row in rows]

    def add_requirement(
        self,
        project_id: str,
        integration_id: str,
        *,
        purpose: str = "",
        required: bool = True,
    ) -> dict[str, Any]:
        if integration_id not in INTEGRATION_BY_ID:
            raise ValueError(f"Unbekannte Integration: {integration_id}")
        with SessionLocal() as db:
            if db.get(Project, project_id) is None:
                raise KeyError(project_id)
            existing = db.scalar(
                select(IntegrationRequirement).where(
                    IntegrationRequirement.project_id == project_id,
                    IntegrationRequirement.integration_id == integration_id,
                )
            )
            if existing:
                existing.purpose = purpose.strip()
                existing.required = required
                row = existing
            else:
                row = IntegrationRequirement(
                    project_id=project_id,
                    integration_id=integration_id,
                    purpose=purpose.strip(),
                    required=required,
                )
                db.add(row)
            db.commit()
            db.refresh(row)
            return requirement_to_dict(row)

    def remove_requirement(self, project_id: str, integration_id: str) -> bool:
        with SessionLocal() as db:
            row = db.scalar(
                select(IntegrationRequirement).where(
                    IntegrationRequirement.project_id == project_id,
                    IntegrationRequirement.integration_id == integration_id,
                )
            )
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True

    def save_configuration(
        self, integration_id: str, values: dict[str, str]
    ) -> dict[str, Any]:
        integration = INTEGRATION_BY_ID.get(integration_id)
        if integration is None:
            raise ValueError(f"Unbekannte Integration: {integration_id}")
        allowed = set(integration["configurable_keys"])
        unexpected = set(values).difference(allowed)
        if unexpected:
            raise ValueError(
                "Nicht erlaubte Konfigurationswerte: " + ", ".join(sorted(unexpected))
            )
        nonempty = {key: value.strip() for key, value in values.items() if value.strip()}
        if "SMTP_PASSWORD" in nonempty:
            # Google displays 16-character app passwords in four groups.
            nonempty["SMTP_PASSWORD"] = "".join(nonempty["SMTP_PASSWORD"].split())
        if not nonempty:
            raise ValueError("Mindestens ein Konfigurationswert ist erforderlich.")
        env_file = Path(os.getenv("MISSION_CONTROL_ENV_FILE", Path.cwd() / ".env"))
        env_file.touch(mode=0o600, exist_ok=True)
        env_file.chmod(0o600)
        for key, value in nonempty.items():
            set_key(str(env_file), key, value, quote_mode="always")
            os.environ[key] = value
        status = integration_status(integration)
        return {
            "id": integration_id,
            "saved_keys": sorted(nonempty),
            "status": status["status"],
            "ready": status["ready"],
        }


integration_service = IntegrationService()
