# Deployment Guide

This document covers production deployment considerations: infrastructure redundancy, health checks, and example deployment configs.

---

## Infrastructure redundancy

### Kafka

- **Development (single broker):** The default `docker-compose.yml` runs one Kafka broker with `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1`. Suitable for local/dev only.
- **Production:** Run a Kafka cluster with at least 3 brokers. Set `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3` and create the `events` topic with `replication.factor=3`. Use a managed Kafka (e.g. Confluent Cloud, MSK) or deploy multiple broker nodes and configure `KAFKA_ADVERTISED_LISTENERS` for all brokers. Update `CAPTURE_KAFKA_BOOTSTRAP_SERVERS` and consumer config with all broker addresses.

### ClickHouse

- **Development:** Single node in Docker is sufficient.
- **Production:** Use replicated ClickHouse (e.g. 2+ nodes with ReplicatedMergeTree) or a managed service (ClickHouse Cloud, Altinity). Ensures query availability and durability.

### PostgreSQL

- **Development:** Single instance in Docker.
- **Production:** Use a managed PostgreSQL (RDS, Cloud SQL) with automated backups and failover. Connection pooling (e.g. PgBouncer) is recommended at high QPS.

### Redis

- **Development:** Single instance in Docker.
- **Production:** Use Redis with persistence (AOF or RDB) and consider Redis Sentinel or a managed Redis for HA. Required for Query API async jobs and query cache.

---

## Health and readiness

| Service      | Health endpoint | Ready check |
|-------------|------------------|-------------|
| Capture API | `GET /health`    | `GET /ready` (Kafka producer connected) |
| Query API   | `GET /health`    | Process up; consider adding ClickHouse ping for `/ready` |
| Auth API    | `GET /health`    | Process up |
| Consumer    | No HTTP          | Scrape `GET /metrics` on `CONSUMER_METRICS_PORT` (default 9090) for liveness |

Use `/ready` for Kubernetes readiness probes and load balancer health so traffic is only sent when dependencies are available.

---

## Resource limits (recommended)

Set CPU/memory limits and requests so the scheduler and autoscaler can behave correctly.

| Component   | CPU request | CPU limit | Memory request | Memory limit |
|------------|-------------|-----------|----------------|--------------|
| Capture API| 100m        | 1000m     | 128Mi          | 512Mi        |
| Consumer   | 200m        | 2000m     | 256Mi          | 1Gi          |
| Query API  | 100m        | 2000m     | 256Mi          | 1Gi          |
| Auth API   | 50m         | 500m      | 64Mi           | 256Mi        |

Adjust based on load testing (see [RUNBOOKS.md](RUNBOOKS.md)).

---

## Kubernetes (example)

- **Deployments:** One Deployment per service (capture-api, consumer, query-api, auth-api). Use the same image with different `command`/args or separate images per service.
- **Probes:** `livenessProbe`: `httpGet /health`; `readinessProbe`: `httpGet /ready` (Capture API), `httpGet /health` (others). Consumer: use a sidecar that serves `/metrics` or a TCP probe to the metrics port.
- **Scaling:** Run multiple replicas of Capture API and Query API behind a Service. Run Consumer with replicas ≤ Kafka partition count; use the same `CONSUMER_KAFKA_GROUP_ID`.
- **Secrets:** Store `POSTGRES_DSN`, `JWT_SECRET`, `REDIS_URL`, and API keys in Secrets; inject via env or volume.
- **ConfigMaps:** Use for non-sensitive config (e.g. `CAPTURE_KAFKA_BOOTSTRAP_SERVERS`, `QUERY_CLICKHOUSE_HOST`).

---

## ECS / Fargate (example)

- Run each service as a separate ECS Service/Task Definition. Use the same pattern: health check on `/health` (and `/ready` for Capture API), environment variables from Secrets Manager or Parameter Store.
- Put Capture API and Query API behind an Application Load Balancer; configure target group health checks to use `/ready` or `/health`.
- Consumer: run as a long-running task; ensure sufficient memory and that the task stays running (no HTTP health required if you use CloudWatch for the metrics port or log-based health).

---

## Applying schema changes

- **ClickHouse:** For new installs, run `infrastructure/init-clickhouse.sh`. For existing installs, run the migration for extracted properties: `schemas/ddl/clickhouse_events_migrate_extracted_props.sql`.
- **PostgreSQL:** Migrations in `infrastructure/init-pg/` run on first start. For new tables or columns, add SQL migrations and run them manually or via a migration job.

---

## Runbooks

See [RUNBOOKS.md](RUNBOOKS.md) for Kafka partitioning, consumer lag, stress tests, and SLOs.
