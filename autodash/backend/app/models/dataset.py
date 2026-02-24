from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.dashboard import DatasetType


class DatasetUploadResponse(BaseModel):
    dataset_id: str


class NumericStats(BaseModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None


class ColumnProfile(BaseModel):
    column: str
    inferred_type: str
    null_percent: float
    distinct_count: int
    numeric_stats: NumericStats | None = None
    top_values: list[dict[str, Any]] = Field(default_factory=list)


class DatasetProfileResponse(BaseModel):
    dataset_id: str
    detected_type: DatasetType
    row_count: int
    column_count: int
    duplicate_rows: int
    quality_score: float
    columns: list[ColumnProfile]

