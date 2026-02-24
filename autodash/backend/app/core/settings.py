from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
DUCKDB_DIR = STORAGE_DIR / "duckdb"
DB_DIR = BASE_DIR / "db"
METADATA_DB_PATH = DB_DIR / "metadata.db"
DUCKDB_PATH = DUCKDB_DIR / "autodash.duckdb"


def ensure_directories() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DUCKDB_DIR.mkdir(parents=True, exist_ok=True)
    DB_DIR.mkdir(parents=True, exist_ok=True)

