# AutoDash

AutoDash is a deterministic analytics SaaS MVP that turns uploaded tabular datasets into ready-made dashboards without manual chart building.

## Stack

- Backend: Python, FastAPI, Pandas, DuckDB, Pydantic, SQLite, local filesystem storage
- Frontend: Next.js (App Router), TypeScript, React, CSS, ECharts
- Data exchange: JSON over REST only

Runtime baseline: Python 3.11+ and Node.js 20+.

## Repository Layout

```text
autodash/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ datasets.py
│  │  │  ├─ dashboard.py
│  │  │  ├─ charts.py
│  │  ├─ core/
│  │  │  ├─ ingestion.py
│  │  │  ├─ profiling.py
│  │  │  ├─ classification.py
│  │  │  ├─ dashboard_generator.py
│  │  │  ├─ chart_engine.py
│  │  ├─ models/
│  │  │  ├─ dataset.py
│  │  │  ├─ dashboard.py
│  │  │  ├─ chart.py
│  │  ├─ utils/
│  │  │  ├─ type_inference.py
│  │  │  ├─ sql_builder.py
│  ├─ storage/
│  │  ├─ uploads/
│  │  ├─ duckdb/
│  ├─ db/
│  │  ├─ metadata.db
├─ frontend/
│  ├─ app/
│  │  ├─ page.tsx
│  │  ├─ dashboard/[id]/page.tsx
│  ├─ components/
│  │  ├─ UploadCard.tsx
│  │  ├─ KPIGrid.tsx
│  │  ├─ ChartRenderer.tsx
│  │  ├─ FilterBar.tsx
│  │  ├─ InsightPanel.tsx
│  ├─ lib/
│  │  ├─ api.ts
│  │  ├─ types.ts
└─ examples/
   └─ dashboard_spec.example.json
```

## Architecture and Flow

1. Upload (`POST /api/v1/datasets/upload`)
- Accepts CSV/XLSX via multipart.
- Stores original file in `backend/storage/uploads`.
- Loads normalized columns into DuckDB table `dataset_<uuid>`.
- Writes dataset metadata to SQLite `backend/db/metadata.db`.

2. Profile (`GET /api/v1/datasets/{dataset_id}/profile`)
- Computes inferred types, null %, distinct counts, numeric stats, top categorical values.
- Computes duplicate rows and a quality score.
- Classifies dataset intent using deterministic rules.

3. Generate dashboard (`POST /api/v1/datasets/{dataset_id}/dashboard/generate`)
- Classifies dataset type:
  - `TIME_SERIES_BUSINESS`
  - `CATEGORICAL_BREAKDOWN`
  - `EVENT_LOG`
  - `NUMERIC_ANALYSIS`
- Builds `DashboardSpec` with KPIs, charts, filters, insights.
- Stores DashboardSpec JSON in SQLite.

4. Fetch dashboard (`GET /api/v1/datasets/{dataset_id}/dashboard`)
- Returns stored DashboardSpec JSON contract.

5. Run chart (`POST /api/v1/datasets/{dataset_id}/chart/run`)
- Looks up chart SQL from stored spec by `chart_id`.
- Injects validated filter clause server-side.
- Executes SQL in DuckDB and returns chart-ready JSON rows.

## Determinism Notes

- No LLM usage in the MVP path.
- Frontend does not infer chart logic or generate SQL.
- All chart SQL originates in backend dashboard generation.
- Frontend only provides filter values and renders returned chart payloads.

## DashboardSpec Contract

```json
{
  "dataset_id": "...",
  "detected_type": "TIME_SERIES_BUSINESS",
  "kpis": [],
  "charts": [],
  "filters": [],
  "insights": [],
  "version": 1,
  "created_at": "ISO8601"
}
```

Example payload: `examples/dashboard_spec.example.json`

## Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:3000`.

## API Summary

- `POST /api/v1/datasets/upload`
- `GET /api/v1/datasets/{dataset_id}/profile`
- `POST /api/v1/datasets/{dataset_id}/dashboard/generate`
- `GET /api/v1/datasets/{dataset_id}/dashboard`
- `POST /api/v1/datasets/{dataset_id}/chart/run`

## Frontend Behavior

- `/` uploads dataset and redirects to dashboard route.
- `/dashboard/[id]`:
  - fetches existing DashboardSpec
  - auto-generates one if missing
  - renders KPIs, filters, charts, insights from spec
  - re-runs chart queries via `/chart/run` when filters change
