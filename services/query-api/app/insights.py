from datetime import date, datetime, timedelta
from typing import Any

from clickhouse_connect.driver import Client

from app.config import settings


def _safe_project(s: str) -> str:
    if not s or not s.replace("-", "").replace("_", "").replace(".", "").isalnum():
        return "default"
    return s[:256]


def _safe_event(s: str) -> str:
    if not s or len(s) > 4096:
        return ""
    return s.replace("'", "\\'")[:4096]


def run_trend(
    client: Client,
    project_id: str,
    event: str,
    date_from: date,
    date_to: date,
    interval: str = "day",
) -> dict[str, Any]:
    project_id = _safe_project(project_id)
    event = _safe_event(event)
    if not event:
        return {"series": [], "labels": []}
    interval_expr = "toStartOfDay(timestamp)" if interval == "day" else "toStartOfWeek(timestamp)" if interval == "week" else "toStartOfMonth(timestamp)"
    q = f"""
    SELECT {interval_expr} AS period, count() AS cnt
    FROM {settings.clickhouse_database}.events
    WHERE project_id = {{project_id:String}} AND event = {{event:String}}
      AND timestamp >= {{date_from:String}} AND timestamp < {{date_to:String}}
    GROUP BY period
    ORDER BY period
    """
    # Format dates as strings for clickhouse-connect parameters
    date_from_str = datetime.combine(date_from, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    date_to_next = date_to + timedelta(days=1)
    date_to_str = datetime.combine(date_to_next, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    params = {
        "project_id": project_id,
        "event": event,
        "date_from": date_from_str,
        "date_to": date_to_str,
    }
    result = client.query(q, parameters=params)
    series = [row[1] for row in result.result_rows]
    labels = [str(row[0]) for row in result.result_rows]
    return {"series": series, "labels": labels}


def run_funnel(
    client: Client,
    project_id: str,
    steps: list[str],
    date_from: date,
    date_to: date,
) -> dict[str, Any]:
    project_id = _safe_project(project_id)
    if len(steps) < 2:
        return {"steps": []}
    # Allowlist event names
    steps = [_safe_event(s) for s in steps[:20]]
    steps = [s for s in steps if s]
    if len(steps) < 2:
        return {"steps": []}
    # Simplified funnel: count distinct_id per step (ordered steps; strict ordering would need subqueries).
    step_counts = []
    # Format dates as strings for clickhouse-connect parameters
    date_from_str = datetime.combine(date_from, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    date_to_next = date_to + timedelta(days=1)
    date_to_str = datetime.combine(date_to_next, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    for i, ev in enumerate(steps):
        q = f"""
        SELECT count(DISTINCT distinct_id) AS cnt
        FROM {settings.clickhouse_database}.events
        WHERE project_id = {{project_id:String}} AND event = {{event:String}}
          AND timestamp >= {{date_from:String}} AND timestamp < {{date_to:String}}
        """
        params = {
            "project_id": project_id,
            "event": ev,
            "date_from": date_from_str,
            "date_to": date_to_str,
        }
        r = client.query(q, parameters=params)
        cnt = r.result_rows[0][0] if r.result_rows else 0
        step_counts.append({"step": i + 1, "event": ev, "count": cnt})
    return {"steps": step_counts}


def run_recent_events(
    client: Client,
    project_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    project_id = _safe_project(project_id)
    limit = min(max(1, limit), 500)
    q = f"""
    SELECT timestamp, distinct_id, event, properties
    FROM {settings.clickhouse_database}.events
    WHERE project_id = {{project_id:String}}
    ORDER BY timestamp DESC
    LIMIT {limit}
    """
    result = client.query(q, parameters={"project_id": project_id})
    rows = []
    for row in result.result_rows:
        ts, distinct_id, event, properties = row
        ts_str = ts.isoformat() if ts and hasattr(ts, "isoformat") else (str(ts) if ts else "")
        rows.append({
            "timestamp": ts_str,
            "distinct_id": distinct_id or "",
            "event": event or "",
            "properties": properties or "{}",
        })
    return rows
