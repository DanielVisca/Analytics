# Query API

FastAPI service: trends, funnels, async heavy queries. Reads from ClickHouse only; no event writes.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

Env: `QUERY_CLICKHOUSE_HOST`, `QUERY_CLICKHOUSE_PORT`, `QUERY_CLICKHOUSE_DATABASE`.

## Endpoints

- `GET /health`
- `GET /api/trends?project_id=&event=&date_from=&date_to=&interval=day|week|month`
- `POST /api/funnels` — body: `{ project_id, steps: string[], date_from, date_to }`
- `POST /api/query/async` — body: `{ project_id, type: trend|funnel, params }` → 202 + job_id
- `GET /api/query/async/{job_id}` — 200 result or 202 pending
- `GET /api/dashboards?project_id=` — list dashboards
- `POST /api/dashboards` — body: `{ project_id, name, layout? }`
- `GET /api/dashboards/{id}?project_id=&with_results=true` — get dashboard, optionally with widget data
- `PATCH /api/dashboards/{id}` — body: `{ project_id, name?, layout? }`
- `DELETE /api/dashboards/{id}?project_id=`
