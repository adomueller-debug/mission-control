import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.services.website_sales_pipeline import website_sales_pipeline


router = APIRouter(prefix="/api/v1", tags=["Sales"])


class ExecuteSalesPipelineRequest(BaseModel):
    city: str = Field(default="Heidelberg", min_length=2, max_length=100)
    max_leads: int = Field(default=20, ge=1, le=20)


@router.post("/sales/website-pipeline/execute")
def execute_website_sales_pipeline(request: ExecuteSalesPipelineRequest):
    try:
        return website_sales_pipeline.execute(
            city=request.city, limit=request.max_leads
        )
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
