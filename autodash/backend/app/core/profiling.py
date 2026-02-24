from __future__ import annotations

import math

import pandas as pd

from app.core.ingestion import get_dataset_metadata, load_dataframe
from app.models.dataset import ColumnProfile, DatasetProfileResponse, NumericStats
from app.utils.type_inference import infer_semantic_type


def _safe_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return float(value)


def _profile_column(name: str, series: pd.Series) -> ColumnProfile:
    inferred_type = infer_semantic_type(series)
    null_percent = round(float(series.isna().mean() * 100), 2)
    distinct_count = int(series.nunique(dropna=True))

    numeric_stats = None
    if inferred_type == "numeric":
        numeric_series = pd.to_numeric(series, errors="coerce").dropna()
        if not numeric_series.empty:
            numeric_stats = NumericStats(
                min=_safe_float(numeric_series.min()),
                max=_safe_float(numeric_series.max()),
                mean=_safe_float(numeric_series.mean()),
                median=_safe_float(numeric_series.median()),
                std=_safe_float(numeric_series.std()),
            )

    top_values: list[dict[str, object]] = []
    if inferred_type in {"categorical", "text", "boolean"}:
        value_counts = series.astype(str).value_counts(dropna=True).head(5)
        top_values = [
            {"value": index, "count": int(count)} for index, count in value_counts.items()
        ]

    return ColumnProfile(
        column=name,
        inferred_type=inferred_type,
        null_percent=null_percent,
        distinct_count=distinct_count,
        numeric_stats=numeric_stats,
        top_values=top_values,
    )


def _quality_score(dataframe: pd.DataFrame, duplicate_rows: int) -> float:
    if dataframe.empty:
        return 0.0

    mean_null_ratio = float(dataframe.isna().mean().mean())
    completeness = 1 - mean_null_ratio

    uniqueness_scores = []
    for column in dataframe.columns:
        distinct = dataframe[column].nunique(dropna=True)
        uniqueness_scores.append(min(float(distinct / max(len(dataframe), 1)), 1.0))
    uniqueness = sum(uniqueness_scores) / max(len(uniqueness_scores), 1)

    duplication_penalty = 1 - (duplicate_rows / max(len(dataframe), 1))

    score = (0.5 * completeness) + (0.3 * uniqueness) + (0.2 * duplication_penalty)
    return round(max(0.0, min(score * 100, 100.0)), 2)


def build_dataset_profile(dataset_id: str, detected_type: str) -> DatasetProfileResponse:
    metadata = get_dataset_metadata(dataset_id)
    if metadata is None:
        raise ValueError("Dataset not found.")

    dataframe = load_dataframe(dataset_id)
    duplicate_rows = int(dataframe.duplicated().sum())

    columns = [_profile_column(name, dataframe[name]) for name in dataframe.columns]
    quality_score = _quality_score(dataframe, duplicate_rows)

    return DatasetProfileResponse(
        dataset_id=dataset_id,
        detected_type=detected_type,  # type: ignore[arg-type]
        row_count=int(len(dataframe)),
        column_count=int(len(dataframe.columns)),
        duplicate_rows=duplicate_rows,
        quality_score=quality_score,
        columns=columns,
    )

