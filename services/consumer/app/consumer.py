import asyncio
import json
import signal
import time
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from clickhouse_connect.driver import Client

from app.clickhouse_client import get_client, insert_batch, row_from_event
from app.config import settings
from app.dlq import send_to_dlq
from app.logging_config import configure_logging, get_logger
from app.metrics import (
    BATCH_SIZE,
    BATCHES_WRITTEN,
    INSERT_ERRORS,
    INSERT_LATENCY,
    MESSAGES_CONSUMED,
    PARSE_ERRORS,
    start_metrics_server,
)

shutdown_event = asyncio.Event()


async def _insert_with_retries(
    client: Client,
    rows: list[tuple],
    log: Any,
) -> bool:
    """Insert batch with retries. Returns True on success, False on final failure."""
    last_error = None
    for attempt in range(settings.insert_retry_count):
        try:
            insert_batch(client, rows)
            return True
        except Exception as e:
            last_error = e
            if attempt < settings.insert_retry_count - 1:
                backoff = settings.insert_retry_backoff_seconds * (2**attempt)
                log.warning(
                    "insert_retry",
                    attempt=attempt + 1,
                    error=str(e),
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)
            else:
                log.error("insert_final_failure", error=str(e))
    return False


async def run_consumer() -> None:
    log = get_logger()
    bootstrap = settings.kafka_bootstrap_servers.split(",")
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=bootstrap,
        group_id=settings.kafka_group_id,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else {},
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
    await consumer.start()
    producer = AIOKafkaProducer(bootstrap_servers=bootstrap)
    await producer.start()
    client = get_client()
    # Buffer (raw, row) for insert and DLQ
    buffer: list[tuple[dict[str, Any], tuple]] = []
    last_flush = time.monotonic()

    try:
        while not shutdown_event.is_set():
            try:
                msg = await asyncio.wait_for(
                    consumer.getone(), timeout=1.0
                )
            except asyncio.TimeoutError:
                now = time.monotonic()
                if len(buffer) >= settings.batch_size or (
                    now - last_flush
                ) >= settings.batch_interval_seconds:
                    if buffer:
                        start = time.perf_counter()
                        raws = [r for r, _ in buffer]
                        rows = [row for _, row in buffer]
                        success = await _insert_with_retries(client, rows, log)
                        INSERT_LATENCY.observe(time.perf_counter() - start)
                        if success:
                            BATCHES_WRITTEN.inc()
                            BATCH_SIZE.observe(len(buffer))
                            log.info("batch_inserted", count=len(buffer))
                        else:
                            INSERT_ERRORS.inc()
                            await send_to_dlq(
                                producer,
                                raws,
                                error_kind="insert_failed",
                                error_message="insert retries exhausted",
                            )
                            log.error("batch_sent_to_dlq", count=len(buffer))
                        await consumer.commit()
                        buffer = []
                    last_flush = now
                continue
            raw = msg.value or {}
            try:
                if not raw.get("event") or not raw.get("distinct_id"):
                    continue
                row = row_from_event(raw)
                buffer.append((raw, row))
                MESSAGES_CONSUMED.inc()
            except Exception as e:
                PARSE_ERRORS.inc()
                log.warning("parse_error", error=str(e), event_id=raw.get("uuid"))
                await send_to_dlq(
                    producer,
                    [raw],
                    error_kind="parse_error",
                    error_message=str(e),
                )
                await consumer.commit()

            now = time.monotonic()
            if len(buffer) >= settings.batch_size or (
                now - last_flush
            ) >= settings.batch_interval_seconds:
                if buffer:
                    start = time.perf_counter()
                    raws = [r for r, _ in buffer]
                    rows = [row for _, row in buffer]
                    success = await _insert_with_retries(client, rows, log)
                    INSERT_LATENCY.observe(time.perf_counter() - start)
                    if success:
                        BATCHES_WRITTEN.inc()
                        BATCH_SIZE.observe(len(buffer))
                        log.info("batch_inserted", count=len(buffer))
                    else:
                        INSERT_ERRORS.inc()
                        await send_to_dlq(
                            producer,
                            raws,
                            error_kind="insert_failed",
                            error_message="insert retries exhausted",
                        )
                        log.error("batch_sent_to_dlq", count=len(buffer))
                    await consumer.commit()
                    buffer = []
                last_flush = now
    finally:
        if buffer:
            start = time.perf_counter()
            raws = [r for r, _ in buffer]
            rows = [row for _, row in buffer]
            success = await _insert_with_retries(client, rows, log)
            INSERT_LATENCY.observe(time.perf_counter() - start)
            if success:
                BATCHES_WRITTEN.inc()
                BATCH_SIZE.observe(len(buffer))
                log.info("final_batch_inserted", count=len(buffer))
            else:
                INSERT_ERRORS.inc()
                await send_to_dlq(
                    producer,
                    raws,
                    error_kind="insert_failed",
                    error_message="insert retries exhausted (shutdown)",
                )
                log.error("final_batch_sent_to_dlq", count=len(buffer))
            await consumer.commit()
        await producer.stop()
        await consumer.stop()


def main() -> None:
    def _on_signal() -> None:
        shutdown_event.set()

    try:
        signal.signal(signal.SIGTERM, lambda *_: _on_signal())
        signal.signal(signal.SIGINT, lambda *_: _on_signal())
    except AttributeError:
        pass  # Windows may not have SIGTERM
    configure_logging()
    start_metrics_server(settings.metrics_port)
    asyncio.run(run_consumer())


if __name__ == "__main__":
    main()
