# Runbooks

## Health and readiness

- **Capture API**
  - `GET /health`: returns 200 when the process is up.
  - `GET /ready`: returns 200 when Kafka producer is connected; 503 when disconnected. Use for load balancer readiness.
- **Query API**: `GET /health` — 200 when up. No dependency check (ClickHouse is checked per query).
- **Auth API**: `GET /health` — 200 when up.
- **Consumer**: No HTTP server; process exit indicates failure. Metrics (and thus basic liveness) are on `CONSUMER_METRICS_PORT` (default 9090); scrape `GET /metrics` to confirm the process is running.

## Observability

- **Logging**: All services use structured JSON logging (e.g. `structlog`) to stdout. Include `error`, `project_id`, and request context in log events.
- **Metrics**: Prometheus metrics are exposed at `GET /metrics` on each HTTP service. Consumer exposes metrics on a separate port (default 9090).
  - Capture: `capture_requests_total`, `capture_request_duration_seconds`, `capture_kafka_produce_*`.
  - Consumer: `consumer_messages_consumed_total`, `consumer_batches_written_total`, `consumer_insert_errors_total`, `consumer_parse_errors_total`, `consumer_dlq_messages_total`.
  - Query: `query_requests_total`, `query_trend_duration_seconds`, `query_funnel_duration_seconds`, `query_errors_total`.
  - Auth: `auth_requests_total`, `auth_request_duration_seconds`.
- **Dashboards**: Point Grafana (or equivalent) at these metrics for SLO dashboards and alerting. Create panels for capture request rate, Kafka produce latency, consumer lag, insert errors, DLQ count, and query latency.

---

## Deployment

- See [DEPLOYMENT.md](DEPLOYMENT.md) for production infrastructure (Kafka replication, ClickHouse, PostgreSQL, Redis), health checks, and example Kubernetes/ECS configs.
- **Deploy order:** Start infrastructure (Kafka, ClickHouse, PostgreSQL, Redis), then Auth API, then Capture API, Consumer(s), Query API. Run ClickHouse DDL and optional migration for extracted properties before or right after first deploy.

---

## API key validation

- **Capture API:** When `CAPTURE_REQUIRE_API_KEY=true`, every `POST /capture` must include a valid `X-API-Key` header. The key is validated against the Auth API; `project_id` is resolved from the key and applied to events. Invalid or missing key returns 401.
- **Query API:** When `QUERY_REQUIRE_API_KEY=true`, requests must include a valid `X-API-Key`; queries and dashboards are scoped to the key’s project. With key optional, passing a valid key still scopes to that project.
- **Creating keys:** Use Auth API `POST /api/projects/{project_id}/api-keys` (with JWT). Store the returned `api_key` securely; it is only shown once.

---

## Dead-letter queue (DLQ)

- Failed events (parse errors or ClickHouse insert after retries) are produced to the **events-dlq** Kafka topic (configurable via `CONSUMER_DLQ_TOPIC`). Each message value is JSON: `raw` (original event), `error_kind`, `error_message`, `dlq_ts`.
- **Inspect:** Consume from `events-dlq` (e.g. `kafka-console-consumer --topic events-dlq --bootstrap-server localhost:9092`) or use a DLQ consumer that logs or forwards to support. Metric `consumer_dlq_messages_total` counts messages sent to DLQ.
- **Replay:** Build a small job that reads from the DLQ topic and re-submits `raw` to the Capture API or writes to ClickHouse after fixing data.

---

## Kafka: partitioning and scaling

### Partition key

- **Always use `distinct_id` as the Kafka message key** when producing events. Same key → same partition → ordering per user and good locality for consumers.
- The Capture API produces with `key = distinct_id` (string encoded as UTF-8). Do not change this without updating consumers and runbooks.

### Partition count

- Start with **12 partitions** for the `events` topic. Formula for scaling:
  - `partitions >= max(producer_throughput_per_partition, consumer_throughput_per_partition)`
  - `partitions >= consumer_group_size` (number of consumer instances)
  - Prefer **2–3x** current consumer count for headroom.
- To **increase partitions** (e.g. when adding more consumer instances):

  ```bash
  docker compose -f infrastructure/docker-compose.yml exec kafka kafka-topics \
    --alter --topic events --partitions 24 --bootstrap-server localhost:9092
  ```

  Consumers will rebalance automatically. Do not reduce partition count (data assignment would break).

### Adding consumers

1. Increase partition count if needed (see above).
2. Start more consumer processes (same `CONSUMER_KAFKA_GROUP_ID`). Each partition is consumed by one consumer in the group.
3. Monitor consumer lag (see below).

### Multiple brokers (later)

- Add more Kafka brokers to the cluster; set `replication.factor` > 1 for the topic.
- Update `CAPTURE_KAFKA_BOOTSTRAP_SERVERS` and consumer config with all broker addresses.

---

## Monitoring consumer lag

- Check lag per partition:

  ```bash
  docker compose -f infrastructure/docker-compose.yml exec kafka kafka-consumer-groups \
    --bootstrap-server localhost:9092 --group event-consumers --describe
  ```

- **Target:** Lag per partition &lt; 10k messages under sustained load. If lag grows:
  - Add more consumer instances (and partitions if needed).
  - Check consumer and ClickHouse insert health and batch size.

---

## Stress test procedure

1. **Start stack:** infra (Kafka, ClickHouse, PostgreSQL, Redis), Capture API, Consumer(s), Query API.
2. **Apply ClickHouse DDL** once: `infrastructure/init-clickhouse.sh localhost:8123`.
3. **Run capture stress test:**  
   `make stress-capture` (or `k6 run tests/stress-capture.js`).  
   Ramp RPS (e.g. 100 → 1k → 5k); run for 10–30 minutes.  
   **Success:** status 202, p99 latency &lt; 200 ms, no sustained error rate.
4. **Check pipeline:** Consumer lag &lt; 10k; ClickHouse row count increases; no consumer errors.
5. **Run query stress test:**  
   `make stress-query` (or `k6 run tests/stress-query.js`).  
   Repeated trend/funnel requests.  
   **Success:** p95 trend &lt; 2s, funnel &lt; 10s, no errors.
6. **Document results:** Note RPS, latency percentiles, and any limits hit. Use these for SLO targets.

---

## SLO summary

| Metric | Target |
|--------|--------|
| Capture API | ≥ N events/s at p99 &lt; 200 ms (N from stress test) |
| Kafka consumer lag | &lt; 10k messages per partition |
| Event visibility | Queryable within ~30 s of ingestion |
| Trend query (7 days) | p95 &lt; 2 s |
| Funnel query (3 steps, 30 days) | p95 &lt; 10 s |
| Health/ready | 200 when dependencies up |
