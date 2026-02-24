from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChartType = Literal["line", "bar", "histogram", "scatter", "missingness"]


class ChartSpec(BaseModel):
    chart_id: str
    title: str
    type: ChartType
    sql: str
    x: str
    y: str
    group_by: str | None = None
    limits: dict[str, Any] = Field(default_factory=dict)


class ChartRunRequest(BaseModel):
    chart_id: str
    filters: dict[str, Any] = Field(default_factory=dict)


class ChartRunResponse(BaseModel):
    chart_id: str
    title: str
    type: ChartType
    x_field: str
    y_field: str
    rows: list[dict[str, Any]]

