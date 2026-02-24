import re
from typing import Any

import pandas as pd


def normalize_column_name(name: Any) -> str:
    raw = str(name).strip().lower()
    raw = re.sub(r"[^a-zA-Z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw or "column"


def _make_unique(values: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique: list[str] = []
    for value in values:
        count = seen.get(value, 0)
        if count == 0:
            unique.append(value)
        else:
            unique.append(f"{value}_{count}")
        seen[value] = count + 1
    return unique


def normalize_dataframe_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    normalized = [normalize_column_name(column) for column in df.columns]
    unique = _make_unique(normalized)
    mapping = {str(original): new for original, new in zip(df.columns, unique)}
    out = df.copy()
    out.columns = unique
    return out, mapping


def infer_semantic_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    non_null = series.dropna()
    if non_null.empty:
        return "categorical"

    sample = non_null.astype(str).head(300)
    parsed = pd.to_datetime(sample, errors="coerce", utc=False, format="mixed")
    parse_ratio = float(parsed.notna().mean())
    if parse_ratio >= 0.8:
        return "datetime"

    distinct = non_null.nunique(dropna=True)
    unique_ratio = distinct / max(len(non_null), 1)
    if unique_ratio > 0.8 and distinct > 50:
        return "text"
    return "categorical"
