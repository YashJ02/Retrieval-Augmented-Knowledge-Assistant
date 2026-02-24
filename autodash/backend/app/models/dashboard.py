from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.chart import ChartSpec


DatasetType = Literal[
    "TIME_SERIES_BUSINESS",
    "CATEGORICAL_BREAKDOWN",
    "EVENT_LOG",
    "NUMERIC_ANALYSIS",
]


class KPIItem(BaseModel):
    kpi_id: str
    title: str
    value: float | int
    format: Literal["number", "percent"]
    description: str | None = None


class FilterSpec(BaseModel):
    filter_id: str
    label: str
    type: Literal["date_range", "categorical", "numeric_range"]
    column: str
    options: list[str] = Field(default_factory=list)
    min: float | str | None = None
    max: float | str | None = None


class InsightItem(BaseModel):
    insight_id: str
    title: str
    description: str
    severity: Literal["info", "warning"] = "info"


class DashboardSpec(BaseModel):
    dataset_id: str
    detected_type: DatasetType
    kpis: list[KPIItem]
    charts: list[ChartSpec]
    filters: list[FilterSpec]
    insights: list[InsightItem]
    version: int = 1
    created_at: datetime

    def as_record(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["created_at"] = self.created_at.isoformat()
        return payload

