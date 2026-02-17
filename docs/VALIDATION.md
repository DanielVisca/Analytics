# Validation Guide

Use this to confirm the full stack is working after setup or changes.

---

## Prerequisites

- **Docker** (for Kafka, ClickHouse, PostgreSQL, Redis)
- **Python 3.10+** with pip (for all services)
- **Node.js 18+** (optional, for dashboard)
- **k6** (optional, for stress tests: `brew install k6`)
- **pytest** (optional, for integration tests: `pip install -r tests/requirements-test.txt`)

---

## 1. Start infrastructure

From the repo root:

```bash
make infra-up
```

Wait ~25 seconds for Kafka and ClickHouse to be ready, then initialize ClickHouse (run once per environment):

```bash
make init-ch
```

If you already had ClickHouse and added the new extracted-property columns, run the migration:

```bash
curl -s "http://localhost:18123/" --data-binary "@schemas/ddl/clickhouse_events_migrate_extracted_props.sql"
```

---

## 2. Start backend services

Use **four terminals** (or run Capture, Consumer, and Query in the background and keep one for commands).

**Terminal 1 – Capture API**

```bash
cd services/capture-api && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 – Consumer**

```bash
cd services/consumer && pip install -r requirements.txt && CONSUMER_CLICKHOUSE_PORT=18123 python -m app.consumer
```

**Terminal 3 – Query API** (needs Redis for async jobs and cache)

```bash
cd services/query-api && pip install -r requirements.txt && QUERY_CLICKHOUSE_PORT=18123 uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Terminal 4 – Auth API**

```bash
cd services/auth-api && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8002
```

Alternatively, use the example script (Capture, Consumer, Query, and demo app; **Auth API not started**):

```bash
./examples/run-all.sh
```

---

## 3. Health checks

In a new terminal:

```bash
# Capture API
curl -s http://localhost:8000/health
# => {"status":"ok"}

curl -s http://localhost:8000/ready
# => {"status":"ready","kafka":"connected"}

# Query API
curl -s http://localhost:8001/health
# => {"status":"ok"}

# Auth API
curl -s http://localhost:8002/health
# => {"status":"ok"}

# Metrics (Capture)
curl -s http://localhost:8000/metrics | head -20
```

Consumer has no HTTP server; it exposes Prometheus metrics on port **9090**:

```bash
curl -s http://localhost:9090/metrics | head -30
```

If all return successfully, the stack is up.

---

## 4. Send an event and query it

**Send one event:**

```bash
curl -s -X POST http://localhost:8000/capture \
  -H "Content-Type: application/json" \
  -d '{"event":"validation_test","distinct_id":"user_1","project_id":"default"}'
# Expect: HTTP 202
```

Wait a few seconds for the consumer to flush, then **run a trend query**:

```bash
curl -s "http://localhost:8001/api/trends?project_id=default&event=validation_test&date_from=2020-01-01&date_to=2030-12-31&interval=day"
# Expect: JSON with "series" and "labels" (may be empty or show 1 count)
```

**Run a funnel query:**

```bash
curl -s -X POST http://localhost:8001/api/funnels \
  -H "Content-Type: application/json" \
  -d '{"project_id":"default","steps":["validation_test"],"date_from":"2020-01-01","date_to":"2030-12-31"}'
# Expect: 400 (need at least 2 steps) or use two events for a valid funnel
```

---

## 5. Integration tests

With the **full stack** (infra + Capture, Consumer, Query, and Redis) running:

```bash
pip install -r tests/requirements-test.txt
make integration-test
```

Or:

```bash
pytest tests/integration/ -v
```

This runs:

- `test_capture_accepts_event` – POST /capture returns 202
- `test_capture_and_trend_e2e` – one event flows to ClickHouse and appears in a trend
- `test_funnel_strict_not_greater_than_simple` – strict funnel counts ≤ simple

---

## 6. Stress tests (optional)

**Capture API** (needs Capture + Consumer + ClickHouse so events are consumed):

```bash
make stress-capture
```

**Query API** (needs Query API + ClickHouse with some data):

```bash
make stress-query
```

See `tests/README.md` and `docs/RUNBOOKS.md` for success criteria and SLOs.

---

## 7. Dashboard (optional)

```bash
make dashboard-dev
```

Open **http://localhost:3000**, connect with Query API URL `http://localhost:8001` and project `default`, then open the dashboard and run a trend (e.g. event `validation_test` or `$pageview`) and a funnel.

---

## Quick reference

| Step              | Command / action                                      |
|-------------------|--------------------------------------------------------|
| Start infra       | `make infra-up`                                       |
| Init ClickHouse   | `make init-ch`                                        |
| Start services    | Four terminals: Capture, Consumer, Query, Auth        |
| Health            | `curl localhost:8000/ready` etc.                      |
| One event + trend | `curl -X POST .../capture` then `curl .../api/trends` |
| Integration tests | `make integration-test`                               |
| Stress tests      | `make stress-capture` / `make stress-query`            |
| Help              | `make help`                                           |

If anything fails, check service logs, `docs/RUNBOOKS.md`, and that Redis (port 6379) and ClickHouse (18123) are reachable from the Query API and Consumer.
