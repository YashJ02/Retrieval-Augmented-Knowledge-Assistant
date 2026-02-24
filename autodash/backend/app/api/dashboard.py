from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.dashboard_generator import generate_dashboard
from app.core.ingestion import get_dashboard_spec
from app.models.dashboard import DashboardSpec


router = APIRouter(prefix="/api/v1/datasets", tags=["dashboard"])


@router.post("/{dataset_id}/dashboard/generate", response_model=DashboardSpec)
def generate_dataset_dashboard(dataset_id: str) -> DashboardSpec:
    try:
        return generate_dashboard(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{dataset_id}/dashboard", response_model=DashboardSpec)
def get_dataset_dashboard(dataset_id: str) -> DashboardSpec:
    spec = get_dashboard_spec(dataset_id)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard spec not found. Generate it first.",
        )
    try:
        return DashboardSpec.model_validate(spec)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

