from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd

from app.core.ingestion import duckdb_connection, get_dashboard_spec, get_dataset_metadata
from app.models.chart import ChartRunResponse
from app.utils.sql_builder import build_filter_clause, inject_filters, validate_select_sql


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _normalize_rows(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in dataframe.to_dict(orient="records"):
        rows.append({key: _normalize_cell(value) for key, value in record.items()})
    return rows


def run_chart(dataset_id: str, chart_id: str, filters: dict[str, Any] | None = None) -> ChartRunResponse:
    metadata = get_dataset_metadata(dataset_id)
    if metadata is None:
        raise ValueError("Dataset not found.")

    spec = get_dashboard_spec(dataset_id)
    if spec is None:
        raise ValueError("Dashboard spec not found. Generate dashboard first.")

    chart_spec = next((chart for chart in spec.get("charts", []) if chart.get("chart_id") == chart_id), None)
    if chart_spec is None:
        raise ValueError("Chart id not found in dashboard spec.")

    sql = chart_spec["sql"]
    validate_select_sql(sql, metadata["table_name"])
    filter_clause, params = build_filter_clause(filters, spec.get("filters", []))
    final_sql = inject_filters(sql, filter_clause)

    with duckdb_connection() as conn:
        dataframe = conn.execute(final_sql, params).df()

    return ChartRunResponse(
        chart_id=chart_spec["chart_id"],
        title=chart_spec["title"],
        type=chart_spec["type"],
        x_field=chart_spec["x"],
        y_field=chart_spec["y"],
        rows=_normalize_rows(dataframe),
    )

