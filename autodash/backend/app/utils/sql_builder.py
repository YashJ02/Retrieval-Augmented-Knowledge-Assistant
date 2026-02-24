from __future__ import annotations

from typing import Any


BLOCKED_SQL_TOKENS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "attach",
    "detach",
    "copy",
    "pragma",
    "create",
}


def quote_identifier(identifier: str) -> str:
    safe = identifier.replace('"', '""')
    return f'"{safe}"'


def validate_select_sql(sql: str, table_name: str) -> None:
    compact = " ".join(sql.strip().lower().split())
    if not compact.startswith("select "):
        raise ValueError("Only SELECT queries are allowed.")
    if ";" in compact:
        raise ValueError("Multi-statement SQL is not allowed.")
    if f'"{table_name.lower()}"' not in compact and table_name.lower() not in compact:
        raise ValueError("SQL does not target the expected dataset table.")
    if any(token in compact for token in BLOCKED_SQL_TOKENS):
        raise ValueError("Blocked SQL token detected.")


def build_filter_clause(
    applied_filters: dict[str, Any] | None,
    filter_specs: list[dict[str, Any]],
) -> tuple[str, list[Any]]:
    if not applied_filters:
        return "", []

    clauses: list[str] = []
    params: list[Any] = []

    for spec in filter_specs:
        filter_id = spec.get("filter_id")
        if filter_id not in applied_filters:
            continue

        value = applied_filters.get(filter_id)
        if value in (None, "", [], {}):
            continue

        column = quote_identifier(spec["column"])
        filter_type = spec["type"]

        if filter_type == "date_range" and isinstance(value, dict):
            start = value.get("start")
            end = value.get("end")
            if start:
                clauses.append(f"TRY_CAST({column} AS TIMESTAMP) >= TRY_CAST(? AS TIMESTAMP)")
                params.append(start)
            if end:
                clauses.append(f"TRY_CAST({column} AS TIMESTAMP) <= TRY_CAST(? AS TIMESTAMP)")
                params.append(end)
        elif filter_type == "numeric_range" and isinstance(value, dict):
            min_value = value.get("min")
            max_value = value.get("max")
            if min_value is not None:
                clauses.append(f"{column} >= ?")
                params.append(min_value)
            if max_value is not None:
                clauses.append(f"{column} <= ?")
                params.append(max_value)
        elif filter_type == "categorical":
            values = value if isinstance(value, list) else [value]
            values = [entry for entry in values if entry not in (None, "")]
            if values:
                placeholders = ", ".join(["?"] * len(values))
                clauses.append(f"{column} IN ({placeholders})")
                params.extend(values)

    if not clauses:
        return "", []

    return " AND " + " AND ".join(clauses), params


def inject_filters(sql: str, filter_clause: str) -> str:
    return sql.replace("{{filters}}", filter_clause)
