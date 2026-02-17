"""Prometheus metrics for Query API."""
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response

REQUESTS_TOTAL = Counter(
    "query_requests_total",
    "Total requests",
    ["method", "path", "status_class"],
)
REQUESTS_LATENCY = Histogram(
    "query_request_duration_seconds",
    "Request latency in seconds",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
TREND_QUERY_LATENCY = Histogram(
    "query_trend_duration_seconds",
    "Trend query latency in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)
FUNNEL_QUERY_LATENCY = Histogram(
    "query_funnel_duration_seconds",
    "Funnel query latency in seconds",
    buckets=(0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)
QUERY_ERRORS = Counter(
    "query_errors_total",
    "Query execution errors",
    ["query_type"],
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
