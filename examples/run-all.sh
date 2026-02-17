#!/usr/bin/env bash
# Run full stack and demo app. From repo root: ./examples/run-all.sh
# Requires: Docker, Python 3 with pip. Install deps first: see examples/README.md
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

# Use the default Docker socket on macOS (Docker Desktop) if DOCKER_HOST is not set
if [ -z "${DOCKER_HOST}" ] && [ -S "/var/run/docker.sock" ]; then
  export DOCKER_HOST=unix:///var/run/docker.sock
fi
if [ -z "${DOCKER_HOST}" ] && [ -S "${HOME}/.docker/run/docker.sock" ]; then
  export DOCKER_HOST=unix://${HOME}/.docker/run/docker.sock
fi

echo "== Checking Docker =="
if ! docker info >/dev/null 2>&1; then
  echo "Docker is not reachable. Try:"
  echo "  1. Open Docker Desktop and wait until it is fully started."
  echo "  2. In a new terminal: docker context use desktop-linux"
  echo "  3. Run: docker ps"
  echo "  Then run this script again. See examples/README.md for more."
  exit 1
fi
echo "Docker OK ($(docker context show 2>/dev/null || true))"

echo "== Starting infrastructure (Kafka, ClickHouse, PostgreSQL, Redis) =="
docker compose -f infrastructure/docker-compose.yml up -d

echo "== Waiting for Kafka and ClickHouse (~25s) =="
sleep 25

echo "== Applying ClickHouse DDL =="
curl -s "http://localhost:18123/" --data-binary "@${REPO}/schemas/ddl/clickhouse_events.sql" || true

echo "== Starting Capture API (port 8000) =="
(cd services/capture-api && pip install -q -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000) &
CAPTURE_PID=$!

echo "== Starting Consumer =="
(cd services/consumer && pip install -q -r requirements.txt && CONSUMER_CLICKHOUSE_PORT=18123 python -m app.consumer) &
CONSUMER_PID=$!

echo "== Starting Query API (port 8001) =="
(cd services/query-api && pip install -q -r requirements.txt && QUERY_CLICKHOUSE_PORT=18123 uvicorn app.main:app --host 0.0.0.0 --port 8001) &
QUERY_PID=$!

echo "== Waiting for Capture API to be ready =="
for i in 1 2 3 4 5 6 7 8 9 10; do
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q 200 && break
  sleep 1
done

echo "== Sending seed events (Python SDK) =="
(cd "$REPO" && pip install -q httpx 2>/dev/null; PYTHONPATH="${REPO}/sdks/python:${REPO}" python examples/send_events.py) || true

echo ""
echo "=============================================="
echo "  Demo app:  http://localhost:8080"
echo "  Query API: http://localhost:8001/docs"
echo "  Capture:   http://localhost:8000"
echo "=============================================="
echo "Serving demo app on port 8080 (Ctrl+C to stop)..."
echo ""

cd examples/demo-app
python3 -m http.server 8080
