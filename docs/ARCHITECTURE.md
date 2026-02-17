# Analytics Platform — System Design & Architecture

This document describes the high-level architecture, data flow, and design decisions for the analytics system.

---

## 1. Overview

The platform ingests analytics events from clients (web or server), buffers them via Kafka, persists them in ClickHouse, and exposes query and dashboard APIs. It is designed as a set of **independent services** with clear boundaries: no service writes to another service’s primary store; each can be developed, deployed, and scaled separately.

---

## 2. High-Level Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌────────────┐
│  Web / SDK  │────▶│  Capture API     │────▶│   Kafka     │────▶│   Consumer      │────▶│ ClickHouse │
│  (browser,  │     │  (FastAPI :8000) │     │   (events   │     │   (batch insert)│     │  (events   │
│   Python)   │     │  validate→Kafka  │     │   topic)    │     │                 │     │   table)   │
└─────────────┘     └──────────────────┘     └─────────────┘     └─────────────────┘     └────────────┘
                                                                                                  │
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐                                  │
│  Dashboard  │────▶│  Query API       │────▶│  PostgreSQL    │                                  │
│  (React     │     │  (FastAPI :8001) │     │  (metadata:    │◀───────────────────────────────────┘
│  :3000)     │     │  trends, funnels,│     │   dashboards,  │   read-only for analytics
│             │     │  dashboards)     │     │   users, keys) │
└─────────────┘     └──────────────────┘     └─────────────────┘

┌─────────────┐     ┌──────────────────┐
│  CLI / API  │────▶│  Auth API        │────▶  PostgreSQL, Redis (optional)
│  (users,    │     │  (FastAPI :8002) │
│   projects, │     │  login, API keys │
│   keys)     │     │                  │
└─────────────┘     └──────────────────┘
```

- **Ingestion path:** SDK → Capture API → Kafka → Consumer → ClickHouse.  
- **Query path:** Dashboard / clients → Query API → ClickHouse (read) + PostgreSQL (metadata).  
- **Auth path:** Clients → Auth API → PostgreSQL (and optional Redis).

---

## 3. Components

| Component        | Responsibility                          | Reads From     | Writes To           | Port / Notes        |
|-----------------|------------------------------------------|----------------|---------------------|---------------------|
| **Capture API** | Validate events, produce to Kafka        | —              | Kafka               | 8000                |
| **Consumer**    | Consume Kafka, enrich (optional), insert | Kafka          | ClickHouse          | N/A (worker)        |
| **Query API**   | Trends, funnels, dashboards, async jobs  | ClickHouse, PG | PostgreSQL (meta)   | 8001                |
| **Auth API**    | Users, projects, API keys, JWT           | PostgreSQL     | PostgreSQL, Redis   | 8002                |
| **Dashboard**   | React UI: connect, trends, funnels       | Query API      | —                   | 3000 (dev)          |
| **Kafka**       | Event buffer, partition by user         | —              | —                   | 9092 (host)         |
| **ClickHouse**  | Event store (columnar, analytical)       | —              | —                   | 18123 (HTTP, host)  |
| **PostgreSQL**  | Metadata (users, projects, dashboards)    | —              | —                   | 5432                |
| **Redis**       | Optional cache / rate limit              | —              | —                   | 6379                |

---

## 4. Data Flow

### 4.1 Event Ingestion

1. **Client** (web SDK or Python SDK) sends a batch of events to `POST /capture` (Capture API).  
2. **Capture API** validates the payload (event name, distinct_id, optional timestamp, properties), resolves project (if auth is used), and produces each event to Kafka with **key = distinct_id** (so all events for one user go to the same partition).  
3. **Kafka** holds the `events` topic; partitions allow parallel consumption.  
4. **Consumer** reads in a consumer group, batches messages (e.g. by count or time), and inserts rows into ClickHouse `analytics.events`.  
5. **ClickHouse** stores events with TTL (e.g. 90 days); ordering key supports fast filters by project, date, and user.

### 4.2 Querying

1. **Dashboard** or any client calls Query API (e.g. `GET /api/trends`, `POST /api/funnels`) with project_id, event(s), and date range.  
2. **Query API** builds parameterized SQL against ClickHouse (no raw user SQL), runs the query, and returns JSON.  
3. For heavy queries, the client can use `POST /api/query/async` and poll `GET /api/query/async/{job_id}` for results.  
4. Dashboard definitions and widget configs are stored in PostgreSQL; Query API reads them and runs the underlying trend/funnel queries.

### 4.3 Auth and Metadata

- **Auth API** manages users, projects, and API keys in PostgreSQL; issues JWTs for dashboard or API access.  
- **Query API** can later validate API key or JWT and scope queries by project.  
- **Capture API** can optionally validate an API key and set project_id from it.

---

## 5. Design Decisions

- **Kafka key = distinct_id:** Keeps ordering per user and good locality for consumers; enables scaling by adding partitions and consumer instances.  
- **ClickHouse for events:** Columnar store suited to aggregations and time-range filters; single-node Docker is enough to start; can scale to clusters later.  
- **PostgreSQL for metadata:** Strong fit for users, projects, dashboards, and API keys; not used for high-volume event rows.  
- **Separate services:** Capture API does not write to ClickHouse; Query API does not write to the event store; Consumer is the only writer to the events table. This keeps boundaries clear and allows independent deployment and scaling.  
- **CORS:** Capture API and Query API send CORS headers so browser-based SDK and Dashboard can call them from different origins.

---

## 6. Scaling and Runbooks

- **Kafka:** Increase partition count when adding more consumer instances; keep partition key as distinct_id. See `docs/RUNBOOKS.md`.  
- **Consumer:** Scale by running more instances (same consumer group) and ensuring partition count ≥ number of instances.  
- **Capture API / Query API:** Scale horizontally behind a load balancer.  
- **ClickHouse:** Start single-node; later add replication and sharding if needed.

---

## 7. Repository Layout (Mapping to Architecture)

| Path                    | Role in Architecture                                |
|-------------------------|------------------------------------------------------|
| `schemas/`              | Event payload and API contracts; ClickHouse DDL      |
| `infrastructure/`       | Docker Compose: Kafka, ClickHouse, PostgreSQL, Redis |
| `services/capture-api/` | Ingestion API (validate → Kafka)                    |
| `services/consumer/`    | Kafka → ClickHouse pipeline                          |
| `services/query-api/`   | Analytics and dashboard backend (ClickHouse + PG)    |
| `services/auth-api/`    | Users, projects, API keys                            |
| `services/dashboard/`   | React UI for Connect and Dashboard                   |
| `sdks/web/`, `sdks/python/` | Client SDKs (capture, batching, retries)       |
| `examples/`             | Demo app and run-all script                          |
| `docs/RUNBOOKS.md`      | Operations: Kafka, scaling, stress tests             |

For a quick visual of the pipeline and how to run it, see the main **README.md**.
