#!/usr/bin/env bash
# Run ClickHouse DDL. Usage: ./init-clickhouse.sh [host]
# Default host: localhost:8123
set -e
HOST="${1:-localhost:8123}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Applying DDL to ClickHouse at $HOST..."
curl -s "http://$HOST/" --data-binary "@${SCRIPT_DIR}/../schemas/ddl/clickhouse_events.sql"
echo "Done."
