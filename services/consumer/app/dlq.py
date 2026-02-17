"""Dead-letter queue: produce failed events to a Kafka topic."""
import json
import time
from typing import Any

from aiokafka import AIOKafkaProducer

from app.config import settings
from app.metrics import DLQ_MESSAGES


async def send_to_dlq(
    producer: AIOKafkaProducer,
    raw_payloads: list[dict[str, Any]],
    error_kind: str,
    error_message: str,
) -> None:
    """Send one or more raw event payloads to the DLQ topic with error context."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for raw in raw_payloads:
        value = json.dumps({
            "raw": raw,
            "error_kind": error_kind,
            "error_message": error_message,
            "dlq_ts": ts,
        }).encode("utf-8")
        key = (raw.get("distinct_id") or "unknown").encode("utf-8")[:4096]
        await producer.send_and_wait(settings.dlq_topic, value=value, key=key)
        DLQ_MESSAGES.inc()
