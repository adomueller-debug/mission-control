from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, SecretStr

from backend.app.services.integration_service import integration_service
from backend.app.services.integration_verifier import verify_integration

router = APIRouter(prefix="/api/v1", tags=["Integrations"])


class IntegrationRequirementRequest(BaseModel):
    integration_id: str = Field(min_length=1, max_length=80)
    purpose: str = Field(default="", max_length=5_000)
    required: bool = True


class IntegrationConfigurationRequest(BaseModel):
    values: dict[str, SecretStr]


@router.get("/integrations")
def list_integrations():
    return integration_service.catalog()


@router.post("/integrations/{integration_id}/configuration")
def save_integration_configuration(
    integration_id: str, request: IntegrationConfigurationRequest
):
    try:
        values = {key: value.get_secret_value() for key, value in request.values.items()}
        return integration_service.save_configuration(integration_id, values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/{integration_id}/verify")
def verify_integration_connection(integration_id: str):
    try:
        return verify_integration(integration_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/integration-requirements")
def list_integration_requirements(project_id: str):
    return integration_service.requirements(project_id)


@router.post("/projects/{project_id}/integration-requirements", status_code=201)
def add_integration_requirement(
    project_id: str, request: IntegrationRequirementRequest
):
    try:
        return integration_service.add_requirement(
            project_id, **request.model_dump()
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/projects/{project_id}/integration-requirements/{integration_id}",
    status_code=204,
)
def remove_integration_requirement(project_id: str, integration_id: str):
    if not integration_service.remove_requirement(project_id, integration_id):
        raise HTTPException(status_code=404, detail="Anforderung nicht gefunden")
    return Response(status_code=204)
