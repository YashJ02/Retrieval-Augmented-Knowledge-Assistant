from __future__ import annotations

import pandas as pd

from app.core.ingestion import load_dataframe, update_detected_type
from app.models.dashboard import DatasetType
from app.utils.type_inference import infer_semantic_type


def _semantic_buckets(dataframe: pd.DataFrame) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "numeric": [],
        "datetime": [],
        "categorical": [],
        "text": [],
        "boolean": [],
    }
    for column in dataframe.columns:
        semantic_type = infer_semantic_type(dataframe[column])
        buckets.setdefault(semantic_type, []).append(column)
    return buckets


def classify_dataframe(dataframe: pd.DataFrame) -> DatasetType:
    buckets = _semantic_buckets(dataframe)
    numeric_count = len(buckets.get("numeric", []))
    datetime_count = len(buckets.get("datetime", []))
    categorical_count = len(buckets.get("categorical", []))
    text_count = len(buckets.get("text", []))

    if datetime_count >= 1:
        if numeric_count >= 1 and len(dataframe) >= 20:
            return "TIME_SERIES_BUSINESS"
        if categorical_count + text_count >= 2:
            return "EVENT_LOG"
    if categorical_count >= 1 and numeric_count >= 1:
        return "CATEGORICAL_BREAKDOWN"
    if numeric_count >= 1:
        return "NUMERIC_ANALYSIS"
    return "CATEGORICAL_BREAKDOWN"


def classify_dataset(dataset_id: str) -> DatasetType:
    dataframe = load_dataframe(dataset_id)
    detected_type = classify_dataframe(dataframe)
    update_detected_type(dataset_id, detected_type)
    return detected_type

