# Analytics system - common targets
# Prereqs: Docker (infra), Python venvs per service, Node.js (dashboard), k6 for stress tests

.PHONY: infra-up infra-down init-ch dashboard-dev dashboard-build stress-capture stress-query help

# Start infrastructure (Kafka, ClickHouse, PostgreSQL, Redis)
infra-up:
	docker compose -f infrastructure/docker-compose.yml up -d

# Stop infrastructure
infra-down:
	docker compose -f infrastructure/docker-compose.yml down

# Run ClickHouse DDL once (after ClickHouse is up on port 18123)
init-ch:
	cd infrastructure && ./init-clickhouse.sh localhost:18123

# Run dashboard in dev mode (requires Node.js/npm, serves on port 3000)
dashboard-dev:
	cd services/dashboard && npm install && npm run dev

# Build dashboard for production (output to services/dashboard/dist)
dashboard-build:
	cd services/dashboard && npm install && npm run build

# Stress test Capture API (requires k6: brew install k6 or see https://k6.io)
# CAPTURE_URL defaults to http://localhost:8000
stress-capture:
	k6 run tests/stress-capture.js

# Stress test Query API (requires Query API on 8001 and data in ClickHouse)
stress-query:
	k6 run tests/stress-query.js

# Show available targets
help:
	@echo "Analytics System - Available targets:"
	@echo ""
	@echo "  Infrastructure:"
	@echo "    make infra-up          Start Docker services (Kafka, ClickHouse, PostgreSQL, Redis)"
	@echo "    make infra-down        Stop Docker services"
	@echo "    make init-ch           Initialize ClickHouse schema (run once after infra-up)"
	@echo ""
	@echo "  Dashboard:"
	@echo "    make dashboard-dev     Run dashboard in dev mode (http://localhost:3000)"
	@echo "    make dashboard-build   Build dashboard for production"
	@echo ""
	@echo "  Load Testing:"
	@echo "    make stress-capture    Run capture API stress test (requires k6)"
	@echo "    make stress-query      Run query API stress test"
	@echo ""
	@echo "  Services (start manually or use examples/run-all.sh):"
	@echo "    cd services/capture-api && .venv/bin/uvicorn app.main:app --port 8000"
	@echo "    cd services/consumer && .venv/bin/python -m app.consumer"
	@echo "    cd services/query-api && .venv/bin/uvicorn app.main:app --port 8001"
	@echo "    cd services/auth-api && .venv/bin/uvicorn app.main:app --port 8002"
	@echo ""
	@echo "  Quick Start:"
	@echo "    1. make infra-up       # Start infrastructure"
	@echo "    2. make init-ch        # Initialize ClickHouse"
	@echo "    3. Start services      # See above or use examples/run-all.sh"
	@echo "    4. make dashboard-dev  # Run dashboard"
