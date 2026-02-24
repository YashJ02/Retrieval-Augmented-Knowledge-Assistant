from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.chart_engine import run_chart
from app.models.chart import ChartRunRequest, ChartRunResponse


router = APIRouter(prefix="/api/v1/datasets", tags=["charts"])


@router.post("/{dataset_id}/chart/run", response_model=ChartRunResponse)
def run_dataset_chart(dataset_id: str, request: ChartRunRequest) -> ChartRunResponse:
    try:
        return run_chart(dataset_id, request.chart_id, request.filters)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

