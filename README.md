# Analytics system

PostHog-style analytics: SDK → Capture API → Kafka → Consumer → ClickHouse; Query API and Auth API for dashboards and user management.

## Layout

- **schemas/** — Event JSON schema, OpenAPI (Capture + Query), ClickHouse DDL
- **infrastructure/** — Docker Compose (Kafka, ClickHouse, PostgreSQL, Redis), init scripts
- **services/capture-api/** — FastAPI ingestion; validate → Kafka (key = distinct_id)
- **services/consumer/** — Kafka consumer → batch insert ClickHouse
- **services/query-api/** — Trends, funnels, async queries, dashboards (reads ClickHouse + PG)
- **services/auth-api/** — Users, projects, API keys (PostgreSQL)
- **services/dashboard/** — React app: Connect (API URL + project) and Dashboard (trends, funnels)
- **sdks/web/** — JS SDK (capture, batching, retries)
- **sdks/python/** — Python SDK (same contract)
- **docs/RUNBOOKS.md** — Kafka partitioning, scaling, stress test procedure
- **examples/** — Demo app (web SDK) and **run-all.sh** to run the full stack and see it in action
- **tests/** — k6 stress tests (capture, query)
- **Makefile** — infra-up, init-ch, stress-capture, stress-query

## Quick start

1. Start infra: `make infra-up`
2. Init ClickHouse: `make init-ch`
3. (Optional) Create topic: see `infrastructure/README.md`
4. Run Capture API: `cd services/capture-api && pip install -r requirements.txt && uvicorn app.main:app --port 8000`
5. Run Consumer: `cd services/consumer && pip install -r requirements.txt && python -m app.consumer`
6. Run Query API: `cd services/query-api && pip install -r requirements.txt && uvicorn app.main:app --port 8001`
7. Run Auth API: `cd services/auth-api && pip install -r requirements.txt && uvicorn app.main:app --port 8002`
8. Run Dashboard: `cd services/dashboard && npm install && npm run dev` → http://localhost:3000

Then: send events to `POST http://localhost:8000/capture`, run trends/funnels at `http://localhost:8001`, manage users/projects at `http://localhost:8002`, and open the dashboard at http://localhost:3000 to connect and view charts.

**See it in action:** From repo root run `./examples/run-all.sh` to start infra + all services and serve the example app at http://localhost:8080. See **examples/README.md**.

## Success criteria and stress tests

See **docs/RUNBOOKS.md**. Run `make stress-capture` and `make stress-query` (requires [k6](https://k6.io)).
