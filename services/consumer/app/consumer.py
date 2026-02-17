import asyncio
import json
import time
from typing import Any

from aiokafka import AIOKafkaConsumer
from clickhouse_connect.driver import Client

from app.clickhouse_client import get_client, insert_batch, row_from_event
from app.config import settings


async def run_consumer() -> None:
    consumer = AIOKafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        group_id=settings.kafka_group_id,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else {},
        auto_offset_reset="earliest",
    )
    await consumer.start()
    client = get_client()
    buffer: list[tuple] = []
    last_flush = time.monotonic()

    try:
        async for msg in consumer:
            try:
                raw: dict[str, Any] = msg.value or {}
                if not raw.get("event") or not raw.get("distinct_id"):
                    continue
                row = row_from_event(raw)
                buffer.append(row)
            except Exception as e:
                print(f"Parse error: {e}")
                continue

            now = time.monotonic()
            if len(buffer) >= settings.batch_size or (now - last_flush) >= settings.batch_interval_seconds:
                if buffer:
                    try:
                        insert_batch(client, buffer)
                        print(f"Inserted {len(buffer)} rows")
                    except Exception as e:
                        print(f"Insert error: {e}")
                    buffer = []
                last_flush = now
    finally:
        if buffer:
            try:
                insert_batch(client, buffer)
            except Exception as e:
                print(f"Final insert error: {e}")
        await consumer.stop()


def main() -> None:
    asyncio.run(run_consumer())


if __name__ == "__main__":
    main()
