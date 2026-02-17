"""
Integration tests for the analytics pipeline.

Requires the full stack to be running: infra (Kafka, ClickHouse, PostgreSQL, Redis),
Capture API, Consumer, Query API. Run from repo root:

  make infra-up
  make init-ch
  # Start Capture API, Consumer, Query API (see README)
  pytest tests/integration/ -v

Environment:
  CAPTURE_URL: default http://localhost:8000
  QUERY_URL:   default http://localhost:8001
"""
import os
import time
import pytest
import httpx

CAPTURE_URL = os.environ.get("CAPTURE_URL", "http://localhost:8000").rstrip("/")
QUERY_URL = os.environ.get("QUERY_URL", "http://localhost:8001").rstrip("/")


def test_capture_accepts_event():
    """POST /capture accepts a single event and returns 202."""
    payload = {
        "event": "integration_test",
        "distinct_id": f"test_user_{int(time.time())}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "properties": {"source": "integration_test"},
        "project_id": "default",
    }
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{CAPTURE_URL}/capture", json=payload)
    assert r.status_code == 202, r.text


def test_capture_and_trend_e2e():
    """One event flows Capture -> Kafka -> Consumer -> ClickHouse; trend query returns 200."""
    event_name = "e2e_trend_test"
    payload = {
        "event": event_name,
        "distinct_id": f"e2e_user_{int(time.time())}",
        "project_id": "default",
    }
    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{CAPTURE_URL}/capture", json=payload)
    assert r.status_code == 202, r.text
    time.sleep(8)  # Allow consumer to flush and ClickHouse to be queryable
    with httpx.Client(timeout=15.0) as client:
        r = client.get(
            f"{QUERY_URL}/api/trends",
            params={
                "project_id": "default",
                "event": event_name,
                "date_from": "2020-01-01",
                "date_to": "2030-12-31",
                "interval": "day",
            },
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "series" in data and "labels" in data


def test_funnel_strict_not_greater_than_simple():
    """Strict funnel step counts should be <= simple funnel (same steps, same range)."""
    date_from = "2020-01-01"
    date_to = "2030-12-31"
    steps = ["$pageview", "button_click", "signup"]
    with httpx.Client(timeout=15.0) as client:
        r_simple = client.post(
            f"{QUERY_URL}/api/funnels",
            json={
                "project_id": "default",
                "steps": steps,
                "date_from": date_from,
                "date_to": date_to,
                "strict": False,
            },
        )
        r_strict = client.post(
            f"{QUERY_URL}/api/funnels",
            json={
                "project_id": "default",
                "steps": steps,
                "date_from": date_from,
                "date_to": date_to,
                "strict": True,
            },
        )
    assert r_simple.status_code == 200 and r_strict.status_code == 200
    simple_steps = r_simple.json().get("steps", [])
    strict_steps = r_strict.json().get("steps", [])
    assert len(simple_steps) == len(strict_steps)
    for s, t in zip(simple_steps, strict_steps):
        assert t["count"] <= s["count"], "Strict funnel count should be <= simple"
