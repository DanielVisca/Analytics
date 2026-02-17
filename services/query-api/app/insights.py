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
    strict: bool = True,
    conversion_window_days: int = 30,
) -> dict[str, Any]:
    project_id = _safe_project(project_id)
    if len(steps) < 2:
        return {"steps": [], "mode": "strict" if strict else "simple"}
    steps = [_safe_event(s) for s in steps[:20]]
    steps = [s for s in steps if s]
    if len(steps) < 2:
        return {"steps": [], "mode": "strict" if strict else "simple"}
    date_from_str = datetime.combine(date_from, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    date_to_next = date_to + timedelta(days=1)
    date_to_str = datetime.combine(date_to_next, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')

    if strict:
        # Same user, steps in order, within conversion_window_days.
        # Subquery: per distinct_id, min(timestamp) for each step event.
        # Outer: count how many have t0 < t1 < ... and (t_last - t_first) <= window per step.
        min_if_parts = [
            f"minIf(timestamp, event = {{step_{i}:String}}) AS t{i}"
            for i in range(len(steps))
        ]
        count_if_parts = []
        for i in range(len(steps)):
            conds = [f"t{j} IS NOT NULL" for j in range(i + 1)]
            if i > 0:
                conds.extend(f"t{j} < t{j+1}" for j in range(i))
                conds.append(
                    f"dateDiff('day', t0, t{i}) <= {conversion_window_days}"
                )
            count_if_parts.append(f"countIf({' AND '.join(conds)}) AS c{i}")
        params: dict[str, Any] = {
            "project_id": project_id,
            "date_from": date_from_str,
            "date_to": date_to_str,
        }
        for i, ev in enumerate(steps):
            params[f"step_{i}"] = ev
        subquery_select = ", ".join(min_if_parts)
        inner_q = f"""
        SELECT distinct_id, {subquery_select}
        FROM {settings.clickhouse_database}.events
        WHERE project_id = {{project_id:String}}
          AND event IN ({', '.join([f'{{step_{i}:String}}' for i in range(len(steps))])})
          AND timestamp >= {{date_from:String}} AND timestamp < {{date_to:String}}
        GROUP BY distinct_id
        """
        count_select = ", ".join(count_if_parts)
        full_q = f"SELECT {count_select} FROM ({inner_q})"
        result = client.query(full_q, parameters=params)
        row = result.result_rows[0] if result.result_rows else tuple(0 for _ in steps)
        step_counts = [
            {"step": i + 1, "event": steps[i], "count": int(row[i])}
            for i in range(len(steps))
        ]
        return {"steps": step_counts, "mode": "strict", "conversion_window_days": conversion_window_days}
    else:
        # Simple: count distinct_id per step independently (no order).
        step_counts = []
        for i, ev in enumerate(steps):
            q = f"""
            SELECT count(DISTINCT distinct_id) AS cnt
            FROM {settings.clickhouse_database}.events
            WHERE project_id = {{project_id:String}} AND event = {{event:String}}
              AND timestamp >= {{date_from:String}} AND timestamp < {{date_to:String}}
            """
            r = client.query(
                q,
                parameters={
                    "project_id": project_id,
                    "event": ev,
                    "date_from": date_from_str,
                    "date_to": date_to_str,
                },
            )
            cnt = r.result_rows[0][0] if r.result_rows else 0
            step_counts.append({"step": i + 1, "event": ev, "count": cnt})
        return {"steps": step_counts, "mode": "simple"}


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
