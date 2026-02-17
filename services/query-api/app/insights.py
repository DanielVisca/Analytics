from datetime import date, datetime
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
      AND timestamp >= {{date_from:DateTime}} AND timestamp < toDateTime({{date_to:Date}}) + INTERVAL 1 DAY
    GROUP BY period
    ORDER BY period
    """
    params = {
        "project_id": project_id,
        "event": event,
        "date_from": datetime.combine(date_from, datetime.min.time()),
        "date_to": date_to,
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
    for i, ev in enumerate(steps):
        q = f"""
        SELECT count(DISTINCT distinct_id) AS cnt
        FROM {settings.clickhouse_database}.events
        WHERE project_id = {{project_id:String}} AND event = {{event:String}}
          AND timestamp >= {{date_from:DateTime}} AND timestamp < toDateTime({{date_to:Date}}) + INTERVAL 1 DAY
        """
        params = {
            "project_id": project_id,
            "event": ev,
            "date_from": datetime.combine(date_from, datetime.min.time()),
            "date_to": date_to,
        }
        r = client.query(q, parameters=params)
        cnt = r.result_rows[0][0] if r.result_rows else 0
        step_counts.append({"step": i + 1, "event": ev, "count": cnt})
    return {"steps": step_counts}
