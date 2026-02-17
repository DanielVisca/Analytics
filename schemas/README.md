# Schemas and contracts

- **events/capture-event.json** — JSON Schema for a single capture event.
- **events/capture-batch.json** — Batch of events (references capture-event).
- **openapi/capture-api.yaml** — OpenAPI 3 for Capture API (ingestion).
- **openapi/query-api.yaml** — OpenAPI 3 for Query/Dashboard API.
- **ddl/clickhouse_events.sql** — ClickHouse table DDL for `analytics.events`.

Event store is read-only from Query API; only the consumer writes to ClickHouse.
