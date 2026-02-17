# Examples

Simple demo app and scripts to run the full analytics stack and see events in action.

## What’s here

- **demo-app/** — Minimal web app that uses the **web SDK**: one HTML page and the SDK in `js/analytics.js`. It sends pageviews and autocapture clicks to the Capture API and has buttons for custom events (`feature_click`, `signup_click`).
- **send_events.py** — Short script that uses the **Python SDK** to send a few events (useful to seed data or run without a browser).
- **run-all.sh** — Starts infrastructure (Docker), Capture API, Consumer, Query API, sends seed events, then serves the demo app on port 8080.

## Prerequisites

- **Docker** (for Kafka, ClickHouse, PostgreSQL, Redis)
- **Python 3.10+** with `pip`
- Install Python deps for the services (once):

  ```bash
  pip install -r services/capture-api/requirements.txt
  pip install -r services/consumer/requirements.txt
  pip install -r services/query-api/requirements.txt
  pip install httpx   # for Python SDK / send_events.py
  ```

## Run everything (one script)

From the **repo root**:

```bash
chmod +x examples/run-all.sh
./examples/run-all.sh
```

This will:

1. Start Docker Compose (Kafka, ClickHouse, PostgreSQL, Redis).
2. Wait for services, apply ClickHouse DDL.
3. Start Capture API (8000), Consumer, and Query API (8001) in the background.
4. Send a few events via the Python SDK.
5. Serve the demo app at **http://localhost:8080** (press Ctrl+C to stop the server only; background processes keep running).

Then:

- Open **http://localhost:8080** — use the demo app (click buttons, navigate; events go to Capture API → Kafka → Consumer → ClickHouse).
- Open **http://localhost:8001/docs** — Query API: try `GET /api/trends` (e.g. `project_id=default`, `event=$pageview`, `date_from` / `date_to`) to see counts over time after some events have been ingested.

**How the demo uses the SDK**

- **Config:** `host` = Capture API URL, `projectId` = `"default"`, `batchSize` = 5, `flushIntervalMs` = 3000, `autocapture` = true.
- **Autocapture (on):** On load it sends a **$pageview** (with `$path`, `$url`, `$title`). Every click sends **$autocapture_click** (with `$tag`, `$text`, `$href`).
- **Custom events:** “I clicked Feature” sends **feature_click** with `{ feature: 'demo_button', name: 'Feature' }`. “Sign up” sends **signup_click** with `{ source: 'demo_app' }`.
- **Flush:** “Flush queue now” sends whatever is in the queue immediately (otherwise events are sent when the queue reaches 5 or after 3 seconds).

So yes — it uses the SDK correctly: same payload shape (event, distinct_id, timestamp, properties, project_id, $lib, $device_id, uuid), batching, and retries. Events are sent to `POST {host}/capture` and end up in ClickHouse for querying.

**Verify events**

1. In the demo, click a few buttons and wait a few seconds (or click “Flush queue now”).
2. Open **http://localhost:8001/docs** → **GET /api/trends**. Use:
   - `project_id`: `default`
   - `event`: `$pageview` or `feature_click` or `signup_click` or `$autocapture_click`
   - `date_from` / `date_to`: today’s date (e.g. `2025-02-16`)
3. Execute; you should see a time series of counts. Events can take up to ~30 seconds to appear (Consumer batch + ClickHouse).

## Run step by step (without run-all.sh)

1. Start infra and init ClickHouse:

   ```bash
   make infra-up
   sleep 25
   make init-ch
   ```

2. In separate terminals, start:

   - Capture API: `cd services/capture-api && uvicorn app.main:app --port 8000`
   - Consumer: `cd services/consumer && python -m app.consumer`
   - Query API: `cd services/query-api && uvicorn app.main:app --port 8001`

3. Seed events (optional):

   ```bash
   PYTHONPATH=sdks/python:. python examples/send_events.py
   ```

4. Serve the demo app:

   ```bash
   cd examples/demo-app && python3 -m http.server 8080
   ```

5. Open http://localhost:8080 and http://localhost:8001/docs as above.

## Demo app config

The page uses the Capture API at `http://localhost:8000` by default. To point elsewhere (e.g. another host/port), set `window.CAPTURE_API_URL` before the SDK loads, or edit the `captureHost` variable in `index.html`.

---

## Troubleshooting: "Cannot connect to the Docker daemon"

If you see this when running `./examples/run-all.sh` or `docker compose`:

1. **Docker Desktop** — Open the Docker Desktop app and wait until the whale icon is steady (not "Starting..."). Then run in a **new terminal**: `docker ps`. If that works, run the script again.
2. **Wrong Docker context** — If you use both Docker Desktop and OrbStack, the CLI might be pointing at the wrong one. Run:
   - `docker context ls`  (current context has a `*`)
   - `docker context use desktop-linux`  (for Docker Desktop) or `docker context use orbstack` (for OrbStack)
   Then try `docker ps` and the script again.
3. **Socket explicitly** — In the same terminal where you run the script, try:
   - `export DOCKER_HOST=unix:///var/run/docker.sock`
   - `./examples/run-all.sh`
   Or with Docker Desktop’s socket: `export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock`
4. **Permission denied on the script** — Run: `chmod +x examples/run-all.sh`
