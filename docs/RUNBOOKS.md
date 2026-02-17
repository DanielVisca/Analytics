# Runbooks

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
