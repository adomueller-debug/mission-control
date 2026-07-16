from fastapi import APIRouter

from backend.app.services.validator import validate_project

router = APIRouter(prefix="/validator", tags=["Validator"])


@router.post("/run")
def run_validation():
    return validate_project()
