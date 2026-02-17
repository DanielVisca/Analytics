import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth_client import validate_api_key as validate_capture_api_key
from app.config import settings
from app.kafka_producer import get_producer, produce_events
from app.logging_config import configure_logging, get_logger
from app.rate_limit import check_rate_limit
from app.metrics import (
    REQUESTS_LATENCY,
    REQUESTS_TOTAL,
    metrics_endpoint,
    status_class,
)
from app.models import normalize_body

producer_holder: dict[str, Any] = {}


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        method = request.method
        path = request.url.path or "/"
        response = await call_next(request)
        duration = time.perf_counter() - start
        sc = status_class(response.status_code)
        REQUESTS_TOTAL.labels(method=method, path=path, status_class=sc).inc()
        REQUESTS_LATENCY.labels(method=method, path=path).observe(duration)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with get_producer() as producer:
        producer_holder["producer"] = producer
        yield
    producer_holder.clear()


app = FastAPI(title="Analytics Capture API", lifespan=lifespan)

app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.add_route("/metrics", metrics_endpoint, methods=["GET"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    if producer_holder.get("producer") is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "kafka": "disconnected"},
        )
    return {"status": "ready", "kafka": "connected"}


@app.post("/capture")
async def capture(request: Request):
    log = get_logger()
    if settings.rate_limit_requests_per_minute > 0:
        rate_key = request.headers.get(settings.rate_limit_key_header) or (request.client.host if request.client else "unknown")
        allowed, retry_after = check_rate_limit(rate_key, settings.rate_limit_requests_per_minute)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
    project_id_override: str | None = None
    if settings.require_api_key:
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if not api_key or not api_key.strip():
            log.warning("capture_missing_api_key")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing API key"},
            )
        project_id_override = await validate_capture_api_key(api_key.strip())
        if not project_id_override:
            log.warning("capture_invalid_api_key")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )
    body_bytes = await request.body()
    if len(body_bytes) > settings.max_request_body_bytes:
        log.warning("request_body_too_large", size=len(body_bytes), limit=settings.max_request_body_bytes)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"Request body too large (max {settings.max_request_body_bytes} bytes)"},
        )
    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError as e:
        log.warning("invalid_json", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid JSON body"},
        )
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Body must be a JSON object"},
        )
    try:
        events_with_keys = normalize_body(body)
    except Exception as e:
        log.warning("normalize_error", error=str(e), errors=getattr(e, "errors", None))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e), "errors": getattr(e, "errors", None)},
        )
    if project_id_override is not None:
        events_with_keys = [
            (ev.model_copy(update={"project_id": project_id_override}), key)
            for ev, key in events_with_keys
        ]
    producer = producer_holder.get("producer")
    if not producer:
        log.error("producer_unavailable")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Producer not available"},
        )
    payloads = [
        (ev.kafka_key().encode("utf-8"), ev.serialized())
        for ev, _ in events_with_keys
    ]
    try:
        await asyncio.wait_for(
            produce_events(producer, payloads),
            timeout=settings.kafka_send_timeout_seconds,
        )
    except asyncio.TimeoutError:
        log.error("kafka_send_timeout")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Event ingestion temporarily unavailable"},
        )
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "accepted"})
