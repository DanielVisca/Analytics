# Infrastructure

## Docker Compose

- **Kafka** (single broker): ports 9092 (host), 29092 (internal). Zookeeper on 2181.
- **ClickHouse**: Host ports 18123 (HTTP) and 19000 (native) to avoid conflict with a local ClickHouse on 8123/9000. No init scripts; run DDL once (see below).
- **PostgreSQL**: 5432, user/pass/db: `analytics` / `analytics` / `analytics`. Schema in `init-pg/`.
- **Redis**: 6379.

### Start

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

### ClickHouse DDL (run once after ClickHouse is up)

```bash
cd infrastructure && ./init-clickhouse.sh localhost:18123
# Or with clickhouse-client: clickhouse-client -h localhost -p 18123 < ../schemas/ddl/clickhouse_events.sql
```

### Kafka topic (optional; auto-create is on)

To pre-create the `events` topic with partitions:

```bash
docker compose -f infrastructure/docker-compose.yml exec kafka kafka-topics \
  --create --topic events --bootstrap-server localhost:9092 --partitions 12 --replication-factor 1
```

## Partitioning and scaling (runbook)

- **Partition key:** Always use `distinct_id` as the Kafka message key when producing. Same user → same partition → ordering and locality.
- **Partition count:** Start with 12. To scale consumers: increase partitions (e.g. 24, 48) and run more consumer instances. Partition count must be >= number of consumer instances.
- **Formula:** `partitions >= max(producer_throughput_per_partition, consumer_throughput_per_partition)` and `partitions >= consumer_group_size`. Prefer 2–3x current consumer count for headroom.
- **Adding partitions:** Use `kafka-topics --alter --topic events --partitions 24 --bootstrap-server ...`. Consumers rebalance automatically.
- **Multiple brokers:** For higher throughput, add more Kafka brokers and set `replication.factor` > 1; update Compose or deploy to K8s.
