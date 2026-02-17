# Analytics system - common targets
# Prereqs: Docker (infra), Python venvs per service, k6 for stress tests

.PHONY: infra-up infra-down init-ch stress-capture stress-query

# Start infrastructure (Kafka, ClickHouse, PostgreSQL, Redis)
infra-up:
	docker compose -f infrastructure/docker-compose.yml up -d

# Stop infrastructure
infra-down:
	docker compose -f infrastructure/docker-compose.yml down

# Run ClickHouse DDL once (after ClickHouse is up)
init-ch:
	cd infrastructure && ./init-clickhouse.sh localhost:8123

# Stress test Capture API (requires k6: brew install k6 or see https://k6.io)
# CAPTURE_URL defaults to http://localhost:8000
stress-capture:
	k6 run tests/stress-capture.js

# Stress test Query API (requires Query API on 8001 and data in ClickHouse)
stress-query:
	k6 run tests/stress-query.js
