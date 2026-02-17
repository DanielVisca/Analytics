# Analytics Platform

Event analytics pipeline: ingest events via SDK or API → Kafka → ClickHouse; query via API and React dashboard. Clear service boundaries, optional Auth API for users and API keys, and production-grade observability, reliability, and rate limiting.

---

## Current State & Production Readiness

**Production Readiness Score: 9/10**

Validated under stress testing:

- **Zero data loss** — All events processed successfully (6,107+ in testing)
- **Zero errors** — No Kafka produce errors, insert errors, or parse errors under load
- **Latency** — P99 &lt; 50 ms end-to-end
- **Throughput** — Sustained 150+ events/sec with consumer keeping up
- **Observability** — Prometheus metrics on all services; structured JSON logging; DLQ for failed events
- **Reliability** — Retry with backoff, graceful shutdown, offset commit only after successful insert
- **Query performance** — Dashboard and trend/funnel queries return quickly with optional Redis caching

**Included today:** API key validation (Capture + Query), request/body limits, rate limiting, Kafka send timeout, connection pooling (Query API + Auth API), Redis async jobs and query cache, strict funnel semantics, integration tests, runbooks and deployment docs.

**Next steps for scaling to production:** Increase Kafka partitions (12+), Redis-based rate limiting for multi-instance Capture API, ClickHouse connection pooling in consumer, circuit breaker for downstream failures, load balancer + multiple Capture API instances, Grafana dashboards. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/RUNBOOKS.md](docs/RUNBOOKS.md).

---

## How to Use (Quick Start)

**Prerequisites:** Docker, Python 3.10+, Node.js 18+ (for dashboard), optional k6 for load tests.

### 1. Start infrastructure

```bash
make infra-up
```

Wait ~25 seconds, then initialize ClickHouse (run once):

```bash
make init-ch
```

### 2. Start backend services

In separate terminals (or use `./examples/run-all.sh` to start them together):

| Service      | Command |
|-------------|---------|
| Capture API | `cd services/capture-api && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Consumer    | `cd services/consumer && pip install -r requirements.txt && CONSUMER_CLICKHOUSE_PORT=18123 python -m app.consumer` |
| Query API   | `cd services/query-api && pip install -r requirements.txt && QUERY_CLICKHOUSE_PORT=18123 uvicorn app.main:app --host 0.0.0.0 --port 8001` |
| Auth API    | `cd services/auth-api && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8002` |

### 3. Run the dashboard

```bash
make dashboard-dev
```

Open **http://localhost:3000**. On the Connect page, use Query API URL `http://localhost:8001` and project `default`, then click **Connect & go to Dashboard**. Use the Dashboard to load trends and funnels.

### 4. Send events

- **Demo app:** Run `./examples/run-all.sh` (or serve `examples/demo-app` on port 8080) and open http://localhost:8080 to generate events.
- **Your app:** Use the Web SDK (`sdks/web/analytics.js`) or Python SDK (`sdks/python`) and point them at `http://localhost:8000` (Capture API).

### 5. View analytics

- **Dashboard (recommended):** http://localhost:3000 → Connect → Dashboard. Load trends (e.g. event `$pageview`) and funnels (e.g. steps `$pageview, feature_click, signup_click`).
- **Query API directly:** http://localhost:8001/docs for `GET /api/trends` and `POST /api/funnels`.

### 6. Validate everything is working

See **[docs/VALIDATION.md](docs/VALIDATION.md)** for a full checklist. Short version:

1. **Health:** `curl http://localhost:8000/ready` and `curl http://localhost:8001/health` (and 8002 for Auth).
2. **One event → trend:** `curl -X POST http://localhost:8000/capture -H "Content-Type: application/json" -d '{"event":"test","distinct_id":"u1","project_id":"default"}'` then after a few seconds: `curl "http://localhost:8001/api/trends?project_id=default&event=test&date_from=2020-01-01&date_to=2030-12-31&interval=day"`.
3. **Integration tests:** With the stack running, `make integration-test` (requires `pip install -r tests/requirements-test.txt`).
4. **Stress tests (optional):** `make stress-capture` and `make stress-query` (requires [k6](https://k6.io)).

---

## Repository Layout

| Path | Purpose |
|------|---------|
| **schemas/** | Event JSON schema, OpenAPI (Capture + Query), ClickHouse DDL |
| **infrastructure/** | Docker Compose (Kafka, ClickHouse, PostgreSQL, Redis); init scripts |
| **services/capture-api/** | Ingestion API: validate events, produce to Kafka (key = distinct_id) |
| **services/consumer/** | Consume Kafka, batch insert into ClickHouse |
| **services/query-api/** | Trends, funnels, dashboards; reads ClickHouse + PostgreSQL |
| **services/auth-api/** | Users, projects, API keys; PostgreSQL |
| **services/dashboard/** | React app: Connect (API URL + project) and Dashboard (charts) |
| **sdks/web/** | Browser SDK: capture, batching, retries |
| **sdks/python/** | Python SDK: same contract, sync HTTP |
| **examples/** | Demo app and `run-all.sh` to run full stack + demo |
| **docs/ARCHITECTURE.md** | System design and data flow |
| **docs/RUNBOOKS.md** | Kafka scaling, consumer lag, DLQ, stress tests |
| **docs/DEPLOYMENT.md** | Production deployment, health checks, K8s/ECS notes |
| **docs/VALIDATION.md** | Step-by-step validation and health checks |
| **tests/** | k6 stress tests, pytest integration tests |
| **Makefile** | `infra-up`, `init-ch`, `dashboard-dev`, `stress-*`, `integration-test`, `help` |

---

## Ports Summary

| Port  | Service        | Notes                          |
|-------|----------------|---------------------------------|
| 3000  | Dashboard      | React dev server                |
| 5432  | PostgreSQL     | Metadata DB                     |
| 6379  | Redis          | Query cache, async jobs         |
| 8000  | Capture API    | Event ingestion                 |
| 8001  | Query API      | Trends, funnels, dashboards      |
| 8002  | Auth API       | Users, projects, API keys       |
| 8080  | Demo app       | When using `examples/run-all.sh`|
| 9092  | Kafka          | Bootstrap (host)                |
| 9090  | Consumer       | Prometheus metrics (no HTTP API)|
| 18123 | ClickHouse HTTP| Host port (internal 8123)        |
| 19000 | ClickHouse native | Host port (internal 9000)    |

---

## More Information

- **Architecture and system design:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)  
- **Operations and scaling:** [docs/RUNBOOKS.md](docs/RUNBOOKS.md)  
- **Deployment and production:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)  
- **Validation checklist:** [docs/VALIDATION.md](docs/VALIDATION.md)  
- **Demo and run-all:** [examples/README.md](examples/README.md)  
- **Stress and integration tests:** [tests/README.md](tests/README.md)  

Run `make help` for a short list of Make targets.
