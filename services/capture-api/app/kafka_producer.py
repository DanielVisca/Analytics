import json
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiokafka import AIOKafkaProducer

from app.config import settings
from app.metrics import (
    KAFKA_PRODUCE_ERRORS,
    KAFKA_PRODUCE_LATENCY,
    KAFKA_PRODUCE_TOTAL,
)


@asynccontextmanager
async def get_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: v if isinstance(v, bytes) else json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()


async def produce_events(producer: AIOKafkaProducer, events: list[tuple[bytes, bytes]]) -> None:
    """Send (key, value) pairs to the events topic. Key = distinct_id."""
    start = time.perf_counter()
    try:
        for key_b, value_b in events:
            await producer.send_and_wait(settings.kafka_topic, value=value_b, key=key_b)
            KAFKA_PRODUCE_TOTAL.inc()
    except Exception:
        KAFKA_PRODUCE_ERRORS.inc()
        raise
    finally:
        KAFKA_PRODUCE_LATENCY.observe(time.perf_counter() - start)
