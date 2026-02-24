from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb
import pandas as pd

from app.core.settings import DUCKDB_PATH, METADATA_DB_PATH, ensure_directories
from app.utils.type_inference import normalize_dataframe_columns


CREATE_DATASETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    table_name TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    detected_type TEXT,
    column_map_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

CREATE_DASHBOARDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dashboards (
    dataset_id TEXT PRIMARY KEY,
    spec_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
);
"""


def initialize_system() -> None:
    ensure_directories()
    with metadata_connection() as conn:
        conn.execute(CREATE_DATASETS_TABLE_SQL)
        conn.execute(CREATE_DASHBOARDS_TABLE_SQL)


@contextmanager
def metadata_connection():
    conn = sqlite3.connect(METADATA_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def duckdb_connection():
    conn = duckdb.connect(str(DUCKDB_PATH))
    try:
        yield conn
    finally:
        conn.close()


def _read_uploaded_dataframe(file_path: Path) -> pd.DataFrame:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    raise ValueError("Unsupported file format. Only CSV and XLSX are supported.")


def ingest_dataset(file_bytes: bytes, filename: str) -> dict[str, str | int]:
    initialize_system()
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise ValueError("Unsupported file type. Please upload CSV or XLSX.")

    dataset_id = str(uuid4())
    stored_name = f"{dataset_id}_{Path(filename).name}"
    from app.core.settings import UPLOAD_DIR  # late import to avoid circular path init

    stored_path = UPLOAD_DIR / stored_name
    stored_path.write_bytes(file_bytes)

    dataframe = _read_uploaded_dataframe(stored_path)
    if dataframe.empty:
        raise ValueError("Uploaded dataset is empty.")

    normalized_df, column_map = normalize_dataframe_columns(dataframe)
    table_name = f"dataset_{dataset_id.replace('-', '_')}"

    with duckdb_connection() as conn:
        conn.register("uploaded_df", normalized_df)
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM uploaded_df')

    now = datetime.now(UTC).isoformat()
    with metadata_connection() as conn:
        conn.execute(
            """
            INSERT INTO datasets (
                dataset_id,
                original_filename,
                stored_path,
                table_name,
                row_count,
                column_count,
                detected_type,
                column_map_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                filename,
                str(stored_path),
                table_name,
                int(len(normalized_df)),
                int(len(normalized_df.columns)),
                None,
                json.dumps(column_map),
                now,
            ),
        )

    return {"dataset_id": dataset_id, "row_count": int(len(normalized_df))}


def get_dataset_metadata(dataset_id: str) -> dict | None:
    initialize_system()
    with metadata_connection() as conn:
        row = conn.execute(
            "SELECT * FROM datasets WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
    if row is None:
        return None
    payload = dict(row)
    payload["column_map"] = json.loads(payload.get("column_map_json") or "{}")
    return payload


def load_dataframe(dataset_id: str) -> pd.DataFrame:
    metadata = get_dataset_metadata(dataset_id)
    if not metadata:
        raise ValueError("Dataset not found.")
    table_name = metadata["table_name"]
    with duckdb_connection() as conn:
        dataframe = conn.execute(f'SELECT * FROM "{table_name}"').df()
    return dataframe


def update_detected_type(dataset_id: str, detected_type: str) -> None:
    with metadata_connection() as conn:
        conn.execute(
            "UPDATE datasets SET detected_type = ? WHERE dataset_id = ?",
            (detected_type, dataset_id),
        )


def save_dashboard_spec(dataset_id: str, spec_json: str) -> None:
    now = datetime.now(UTC).isoformat()
    with metadata_connection() as conn:
        conn.execute(
            """
            INSERT INTO dashboards (dataset_id, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (dataset_id, spec_json, now, now),
        )


def get_dashboard_spec(dataset_id: str) -> dict | None:
    with metadata_connection() as conn:
        row = conn.execute(
            "SELECT spec_json FROM dashboards WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["spec_json"])

