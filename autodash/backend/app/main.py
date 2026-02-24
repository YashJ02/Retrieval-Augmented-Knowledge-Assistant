from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.charts import router as charts_router
from app.api.dashboard import router as dashboard_router
from app.api.datasets import router as datasets_router
from app.core.ingestion import initialize_system


app = FastAPI(
    title="AutoDash API",
    version="1.0.0",
    description="Deterministic dataset-to-dashboard analytics backend.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_router)
app.include_router(dashboard_router)
app.include_router(charts_router)


@app.on_event("startup")
def on_startup() -> None:
    initialize_system()


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
