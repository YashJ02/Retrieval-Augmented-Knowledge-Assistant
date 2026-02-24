from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.classification import classify_dataset
from app.core.ingestion import ingest_dataset
from app.core.profiling import build_dataset_profile
from app.models.dataset import DatasetProfileResponse, DatasetUploadResponse


router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetUploadResponse:
    filename = file.filename or "uploaded.csv"
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in {"csv", "xlsx", "xls"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload CSV or XLSX.",
        )

    try:
        payload = ingest_dataset(await file.read(), filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return DatasetUploadResponse(dataset_id=str(payload["dataset_id"]))


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(dataset_id: str) -> DatasetProfileResponse:
    try:
        detected_type = classify_dataset(dataset_id)
        return build_dataset_profile(dataset_id, detected_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

