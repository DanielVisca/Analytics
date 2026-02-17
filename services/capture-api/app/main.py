from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.kafka_producer import get_producer, produce_events
from app.models import normalize_body

producer_holder: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with get_producer() as producer:
        producer_holder["producer"] = producer
        yield
    producer_holder.clear()


app = FastAPI(title="Analytics Capture API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


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
    try:
        body = await request.json()
    except Exception:
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
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(e), "errors": getattr(e, "errors", None)},
        )
    producer = producer_holder.get("producer")
    if not producer:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Producer not available"},
        )
    # Serialize to (key_bytes, value_bytes) for Kafka; key = distinct_id
    payloads = [
        (ev.kafka_key().encode("utf-8"), ev.serialized())
        for ev, _ in events_with_keys
    ]
    await produce_events(producer, payloads)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "accepted"})
