# Capture API

FastAPI service: validates events, produces to Kafka (key = `distinct_id`), returns 202.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Env: `CAPTURE_KAFKA_BOOTSTRAP_SERVERS=localhost:9092`, `CAPTURE_KAFKA_TOPIC=events`.

## Endpoints

- `GET /health` — liveness
- `GET /ready` — Kafka producer connected
- `POST /capture` — body: single event or `{ "batch": [...] }`. Returns 202 Accepted.
