"""Prometheus metrics for Consumer."""
from prometheus_client import Counter, Histogram, start_http_server

# Consumer metrics
MESSAGES_CONSUMED = Counter(
    "consumer_messages_consumed_total",
    "Total messages consumed from Kafka",
)
BATCHES_WRITTEN = Counter(
    "consumer_batches_written_total",
    "Total batches successfully written to ClickHouse",
)
BATCH_SIZE = Histogram(
    "consumer_batch_size",
    "Number of events per batch written",
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000),
)
INSERT_ERRORS = Counter(
    "consumer_insert_errors_total",
    "ClickHouse insert errors",
)
PARSE_ERRORS = Counter(
    "consumer_parse_errors_total",
    "Event parse errors",
)
DLQ_MESSAGES = Counter(
    "consumer_dlq_messages_total",
    "Messages sent to dead-letter queue",
)
INSERT_LATENCY = Histogram(
    "consumer_insert_duration_seconds",
    "ClickHouse insert latency in seconds",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def start_metrics_server(port: int = 9090) -> None:
    """Start HTTP server for Prometheus scraping."""
    start_http_server(port)
