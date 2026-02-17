# Python SDK

Thin client: same event payload as web SDK, sync HTTP with batching and retries.

## Install

```bash
pip install httpx
```

## Usage

```python
from analytics import Analytics

client = Analytics(
    host="http://localhost:8000",
    api_key="optional",
    project_id="my-project",
    batch_size=10,
    flush_interval_seconds=5.0,
    max_retries=3,
)
client.capture("signup", {"plan": "pro"})
client.flush()  # optional; auto-flush on batch size or interval
```
