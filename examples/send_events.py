#!/usr/bin/env python3
"""Send a few events via the Python SDK. Run after Capture API is up (e.g. http://localhost:8000)."""
import sys
from pathlib import Path

# Add repo root and sdks/python so we can import the SDK
repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
sys.path.insert(0, str(repo / "sdks" / "python"))

from analytics import Analytics

CAPTURE_URL = "http://localhost:8000"

def main():
    client = Analytics(
        host=CAPTURE_URL,
        project_id="default",
        batch_size=5,
        flush_interval_seconds=1,
    )
    client.capture("demo_pageview", {"page": "examples", "source": "send_events.py"})
    client.capture("demo_action", {"action": "run_script"})
    client.capture("signup_click", {"source": "python_example"})
    client.flush()
    print("Sent 3 events to", CAPTURE_URL)

if __name__ == "__main__":
    main()
