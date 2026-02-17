# Consumer

Consumes from Kafka topic `events`, batches messages, inserts into ClickHouse `analytics.events`.

## Run

Ensure Kafka and ClickHouse are up and DDL has been applied.

```bash
pip install -r requirements.txt
python -m app.consumer
```

Env: `CONSUMER_KAFKA_BOOTSTRAP_SERVERS`, `CONSUMER_CLICKHOUSE_HOST`, `CONSUMER_BATCH_SIZE` (default 1000), `CONSUMER_BATCH_INTERVAL_SECONDS` (default 5).
