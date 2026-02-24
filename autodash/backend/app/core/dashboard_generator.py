from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from itertools import combinations

import pandas as pd

from app.core.classification import classify_dataframe
from app.core.ingestion import (
    get_dataset_metadata,
    load_dataframe,
    save_dashboard_spec,
    update_detected_type,
)
from app.models.chart import ChartSpec
from app.models.dashboard import DashboardSpec, FilterSpec, InsightItem, KPIItem
from app.utils.type_inference import infer_semantic_type


def _safe_number(value: float | int | None) -> float | int:
    if value is None:
        return 0
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return 0
    return round(float(value), 4)


def _build_semantic_map(dataframe: pd.DataFrame) -> dict[str, str]:
    return {column: infer_semantic_type(dataframe[column]) for column in dataframe.columns}


def _pick_primary_metric(dataframe: pd.DataFrame, numeric_columns: list[str]) -> str | None:
    if not numeric_columns:
        return None
    ranked = sorted(
        numeric_columns,
        key=lambda col: (
            int(pd.to_numeric(dataframe[col], errors="coerce").notna().sum()),
            float(pd.to_numeric(dataframe[col], errors="coerce").std(skipna=True) or 0.0),
        ),
        reverse=True,
    )
    return ranked[0]


def _pick_primary_category(dataframe: pd.DataFrame, categorical_columns: list[str]) -> str | None:
    if not categorical_columns:
        return None
    preferred = [
        col
        for col in categorical_columns
        if 2 <= int(dataframe[col].nunique(dropna=True)) <= 50
    ]
    return preferred[0] if preferred else categorical_columns[0]


def _pick_primary_time(datetime_columns: list[str]) -> str | None:
    return datetime_columns[0] if datetime_columns else None


def _compute_growth_percent(
    dataframe: pd.DataFrame, time_column: str | None, metric_column: str | None
) -> float | None:
    if not time_column or not metric_column:
        return None

    dt_series = pd.to_datetime(dataframe[time_column], errors="coerce")
    metric_series = pd.to_numeric(dataframe[metric_column], errors="coerce")
    temp = pd.DataFrame({"dt": dt_series, "metric": metric_series}).dropna()
    if temp.empty:
        return None

    monthly = temp.set_index("dt").resample("ME")["metric"].sum().dropna()
    if len(monthly) < 2:
        return None

    first = float(monthly.iloc[0])
    last = float(monthly.iloc[-1])
    if first == 0:
        return None
    return ((last - first) / abs(first)) * 100.0


def _build_kpis(
    dataframe: pd.DataFrame, metric_column: str | None, growth_percent: float | None
) -> list[KPIItem]:
    kpis: list[KPIItem] = [
        KPIItem(
            kpi_id="row_count",
            title="Row Count",
            value=int(len(dataframe)),
            format="number",
            description="Total number of records.",
        )
    ]

    if metric_column:
        metric_series = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
        if not metric_series.empty:
            kpis.extend(
                [
                    KPIItem(
                        kpi_id="metric_sum",
                        title=f"{metric_column} Sum",
                        value=_safe_number(metric_series.sum()),
                        format="number",
                    ),
                    KPIItem(
                        kpi_id="metric_avg",
                        title=f"{metric_column} Avg",
                        value=_safe_number(metric_series.mean()),
                        format="number",
                    ),
                    KPIItem(
                        kpi_id="metric_min",
                        title=f"{metric_column} Min",
                        value=_safe_number(metric_series.min()),
                        format="number",
                    ),
                    KPIItem(
                        kpi_id="metric_max",
                        title=f"{metric_column} Max",
                        value=_safe_number(metric_series.max()),
                        format="number",
                    ),
                ]
            )

    if growth_percent is not None:
        kpis.append(
            KPIItem(
                kpi_id="growth_percent",
                title="Growth %",
                value=_safe_number(growth_percent),
                format="percent",
                description="Relative growth from first to last monthly bucket.",
            )
        )

    if len(kpis) < 3:
        kpis.append(
            KPIItem(
                kpi_id="column_count",
                title="Column Count",
                value=int(len(dataframe.columns)),
                format="number",
            )
        )

    return kpis[:6]


def _build_filters(
    dataframe: pd.DataFrame,
    time_column: str | None,
    category_columns: list[str],
    metric_column: str | None,
) -> list[FilterSpec]:
    filters: list[FilterSpec] = []

    if time_column:
        dt_series = pd.to_datetime(dataframe[time_column], errors="coerce").dropna()
        if not dt_series.empty:
            filters.append(
                FilterSpec(
                    filter_id=f"{time_column}_range",
                    label=f"{time_column} Range",
                    type="date_range",
                    column=time_column,
                    min=dt_series.min().date().isoformat(),
                    max=dt_series.max().date().isoformat(),
                )
            )

    for column in category_columns[:3]:
        distinct = int(dataframe[column].nunique(dropna=True))
        if 1 < distinct <= 40:
            values = sorted(dataframe[column].dropna().astype(str).unique().tolist())[:40]
            filters.append(
                FilterSpec(
                    filter_id=f"{column}_values",
                    label=column,
                    type="categorical",
                    column=column,
                    options=values,
                )
            )

    if metric_column:
        metric = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
        if not metric.empty:
            filters.append(
                FilterSpec(
                    filter_id=f"{metric_column}_range",
                    label=f"{metric_column} Range",
                    type="numeric_range",
                    column=metric_column,
                    min=float(metric.min()),
                    max=float(metric.max()),
                )
            )

    return filters


def _best_scatter_pair(dataframe: pd.DataFrame, numeric_columns: list[str]) -> tuple[str, str, float] | None:
    if len(numeric_columns) < 2:
        return None

    numeric_df = dataframe[numeric_columns].apply(pd.to_numeric, errors="coerce")
    best_pair: tuple[str, str, float] | None = None
    for left, right in combinations(numeric_columns, 2):
        corr_value = numeric_df[left].corr(numeric_df[right])
        if corr_value is None or math.isnan(corr_value):
            continue
        if best_pair is None or abs(corr_value) > abs(best_pair[2]):
            best_pair = (left, right, float(corr_value))
    return best_pair


def _build_charts(
    dataframe: pd.DataFrame,
    table_name: str,
    time_column: str | None,
    category_column: str | None,
    metric_column: str | None,
    scatter_pair: tuple[str, str, float] | None,
) -> list[ChartSpec]:
    charts: list[ChartSpec] = []
    fallback_category = category_column or str(dataframe.columns[0])

    if time_column and metric_column:
        charts.append(
            ChartSpec(
                chart_id="line_metric_over_time",
                title=f"{metric_column} Over Time",
                type="line",
                sql=(
                    f'SELECT date_trunc(\'day\', TRY_CAST("{time_column}" AS TIMESTAMP))::DATE AS x, '
                    f'SUM("{metric_column}") AS y '
                    f'FROM "{table_name}" '
                    f'WHERE TRY_CAST("{time_column}" AS TIMESTAMP) IS NOT NULL '
                    f'AND "{metric_column}" IS NOT NULL {{{{filters}}}} '
                    "GROUP BY 1 ORDER BY 1 LIMIT 365"
                ),
                x="x",
                y="y",
                limits={"max_points": 365},
            )
        )
    elif time_column:
        charts.append(
            ChartSpec(
                chart_id="line_record_volume",
                title="Record Volume Over Time",
                type="line",
                sql=(
                    f'SELECT date_trunc(\'day\', TRY_CAST("{time_column}" AS TIMESTAMP))::DATE AS x, COUNT(*) AS y '
                    f'FROM "{table_name}" '
                    f'WHERE TRY_CAST("{time_column}" AS TIMESTAMP) IS NOT NULL {{{{filters}}}} '
                    "GROUP BY 1 ORDER BY 1 LIMIT 365"
                ),
                x="x",
                y="y",
                limits={"max_points": 365},
            )
        )

    metric_aggregate = f'SUM("{metric_column}")' if metric_column else "COUNT(*)"
    charts.append(
        ChartSpec(
            chart_id="bar_top_categories",
            title=f"Top {fallback_category}",
            type="bar",
            sql=(
                f'SELECT "{fallback_category}" AS x, {metric_aggregate} AS y '
                f'FROM "{table_name}" '
                f'WHERE "{fallback_category}" IS NOT NULL {{{{filters}}}} '
                "GROUP BY 1 ORDER BY y DESC LIMIT 12"
            ),
            x="x",
            y="y",
            group_by=fallback_category,
            limits={"top_n": 12},
        )
    )

    if metric_column:
        metric_values = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
        min_value = float(metric_values.min()) if not metric_values.empty else 0.0
        max_value = float(metric_values.max()) if not metric_values.empty else 0.0
        bin_size = max((max_value - min_value) / 10, 1e-9) if max_value > min_value else 1.0
        charts.append(
            ChartSpec(
                chart_id="hist_metric_distribution",
                title=f"{metric_column} Distribution",
                type="histogram",
                sql=(
                    f'SELECT FLOOR((CAST("{metric_column}" AS DOUBLE) - {min_value}) / {bin_size}) AS x, '
                    f'COUNT(*) AS y '
                    f'FROM "{table_name}" '
                    f'WHERE "{metric_column}" IS NOT NULL {{{{filters}}}} '
                    "GROUP BY 1 ORDER BY 1 LIMIT 30"
                ),
                x="x",
                y="y",
                limits={"bins": 10},
            )
        )
    else:
        charts.append(
            ChartSpec(
                chart_id="bar_value_frequency",
                title=f"{fallback_category} Frequency",
                type="bar",
                sql=(
                    f'SELECT "{fallback_category}" AS x, COUNT(*) AS y '
                    f'FROM "{table_name}" '
                    f'WHERE "{fallback_category}" IS NOT NULL {{{{filters}}}} '
                    "GROUP BY 1 ORDER BY y DESC LIMIT 20"
                ),
                x="x",
                y="y",
            )
        )

    if scatter_pair:
        x_col, y_col, _ = scatter_pair
        charts.append(
            ChartSpec(
                chart_id="scatter_best_correlation",
                title=f"{x_col} vs {y_col}",
                type="scatter",
                sql=(
                    f'SELECT "{x_col}" AS x, "{y_col}" AS y '
                    f'FROM "{table_name}" '
                    f'WHERE "{x_col}" IS NOT NULL AND "{y_col}" IS NOT NULL {{{{filters}}}} '
                    "LIMIT 2000"
                ),
                x="x",
                y="y",
                limits={"max_points": 2000},
            )
        )
    else:
        charts.append(
            ChartSpec(
                chart_id="bar_record_count",
                title="Record Count Snapshot",
                type="bar",
                sql=(
                    f'SELECT \'records\' AS x, COUNT(*) AS y '
                    f'FROM "{table_name}" '
                    "WHERE 1=1 {{filters}} "
                    "GROUP BY 1"
                ),
                x="x",
                y="y",
            )
        )

    missing_union = " UNION ALL ".join(
        [
            (
                f"SELECT '{column}' AS x, "
                f'SUM(CASE WHEN "{column}" IS NULL THEN 1 ELSE 0 END) AS y '
                f'FROM "{table_name}" WHERE 1=1 {{{{filters}}}}'
            )
            for column in dataframe.columns[:12]
        ]
    )
    charts.append(
        ChartSpec(
            chart_id="missingness_overview",
            title="Missing Values by Column",
            type="missingness",
            sql=f"{missing_union} ORDER BY y DESC LIMIT 12",
            x="x",
            y="y",
        )
    )

    return charts[:8]


def _build_insights(
    dataframe: pd.DataFrame,
    time_column: str | None,
    category_column: str | None,
    metric_column: str | None,
    growth_percent: float | None,
    scatter_pair: tuple[str, str, float] | None,
) -> list[InsightItem]:
    insights: list[InsightItem] = []

    if growth_percent is not None:
        direction = "increased" if growth_percent >= 0 else "decreased"
        insights.append(
            InsightItem(
                insight_id="trend_growth",
                title="Trend",
                description=f"Primary metric {direction} by {round(abs(growth_percent), 2)}% across the observed period.",
            )
        )

    if category_column:
        grouped = dataframe[category_column].astype(str).value_counts(dropna=True)
        if not grouped.empty:
            top_category = grouped.index[0]
            top_count = int(grouped.iloc[0])
            insights.append(
                InsightItem(
                    insight_id="top_contributor",
                    title="Top Contributor",
                    description=f"{top_category} is the largest segment with {top_count} records.",
                )
            )

    if metric_column:
        numeric = pd.to_numeric(dataframe[metric_column], errors="coerce").dropna()
        if len(numeric) > 5 and float(numeric.std()) > 0:
            z_scores = (numeric - float(numeric.mean())) / float(numeric.std())
            outlier_count = int((z_scores.abs() > 3).sum())
            if outlier_count > 0:
                insights.append(
                    InsightItem(
                        insight_id="outliers",
                        title="Outliers",
                        description=f"Detected {outlier_count} outlier rows in {metric_column} (|z| > 3).",
                        severity="warning",
                    )
                )

    if scatter_pair and abs(scatter_pair[2]) >= 0.6:
        direction = "positive" if scatter_pair[2] > 0 else "negative"
        insights.append(
            InsightItem(
                insight_id="correlation",
                title="Correlation",
                description=(
                    f"{scatter_pair[0]} and {scatter_pair[1]} show a {direction} correlation "
                    f"(r={round(scatter_pair[2], 2)})."
                ),
            )
        )

    if not insights:
        insights.append(
            InsightItem(
                insight_id="baseline",
                title="Baseline",
                description=(
                    f"Dataset has {len(dataframe)} rows and {len(dataframe.columns)} columns. "
                    "Apply filters to refine trends."
                ),
            )
        )

    return insights


def generate_dashboard(dataset_id: str) -> DashboardSpec:
    metadata = get_dataset_metadata(dataset_id)
    if metadata is None:
        raise ValueError("Dataset not found.")

    dataframe = load_dataframe(dataset_id)
    semantic_map = _build_semantic_map(dataframe)
    datetime_columns = [k for k, v in semantic_map.items() if v == "datetime"]
    numeric_columns = [k for k, v in semantic_map.items() if v == "numeric"]
    categorical_columns = [k for k, v in semantic_map.items() if v in {"categorical", "text", "boolean"}]

    detected_type = classify_dataframe(dataframe)
    update_detected_type(dataset_id, detected_type)

    primary_time = _pick_primary_time(datetime_columns)
    primary_metric = _pick_primary_metric(dataframe, numeric_columns)
    primary_category = _pick_primary_category(dataframe, categorical_columns)
    best_pair = _best_scatter_pair(dataframe, numeric_columns)
    growth_percent = _compute_growth_percent(dataframe, primary_time, primary_metric)

    kpis = _build_kpis(dataframe, primary_metric, growth_percent)
    filters = _build_filters(dataframe, primary_time, categorical_columns, primary_metric)
    charts = _build_charts(
        dataframe=dataframe,
        table_name=metadata["table_name"],
        time_column=primary_time,
        category_column=primary_category,
        metric_column=primary_metric,
        scatter_pair=best_pair,
    )
    insights = _build_insights(
        dataframe=dataframe,
        time_column=primary_time,
        category_column=primary_category,
        metric_column=primary_metric,
        growth_percent=growth_percent,
        scatter_pair=best_pair,
    )

    spec = DashboardSpec(
        dataset_id=dataset_id,
        detected_type=detected_type,
        kpis=kpis,
        charts=charts,
        filters=filters,
        insights=insights,
        version=1,
        created_at=datetime.now(UTC),
    )

    save_dashboard_spec(dataset_id, json.dumps(spec.as_record()))
    return spec
