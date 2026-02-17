"""Prometheus metrics for Capture API."""
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response

# Request counts
REQUESTS_TOTAL = Counter(
    "capture_requests_total",
    "Total capture requests",
    ["method", "path", "status_class"],
)
REQUESTS_LATENCY = Histogram(
    "capture_request_duration_seconds",
    "Request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
# Kafka produce
KAFKA_PRODUCE_TOTAL = Counter(
    "capture_kafka_produce_total",
    "Total events sent to Kafka",
)
KAFKA_PRODUCE_ERRORS = Counter(
    "capture_kafka_produce_errors_total",
    "Kafka produce errors",
)
KAFKA_PRODUCE_LATENCY = Histogram(
    "capture_kafka_produce_duration_seconds",
    "Kafka produce latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def status_class(status_code: int) -> str:
    if status_code < 400:
        return "2xx"
    if status_code < 500:
        return "4xx"
    return "5xx"


async def metrics_endpoint(_request: Request) -> Response:
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
