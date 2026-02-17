from datetime import date
from typing import Any, Optional

from psycopg2.extras import Json

from app.db import get_clickhouse
from app.insights import run_funnel, run_trend
from app.db_pg import get_pg_conn


def dashboard_crud_list(project_id: str) -> list[dict[str, Any]]:
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, project_id, name, layout, created_at, updated_at FROM dashboards WHERE project_id = %s ORDER BY updated_at DESC",
                (project_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": str(r["id"]),
                "project_id": str(r["project_id"]),
                "name": r["name"],
                "layout": r["layout"],
                "created_at": str(r["created_at"]),
                "updated_at": str(r["updated_at"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def dashboard_crud_get(dashboard_id: str, project_id: str) -> Optional[dict[str, Any]]:
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, project_id, name, layout FROM dashboards WHERE id = %s AND project_id = %s",
                (dashboard_id, project_id),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "name": row["name"],
            "layout": row["layout"] or [],
        }
    finally:
        conn.close()


def dashboard_crud_create(project_id: str, name: str, layout: Optional[list[Any]] = None) -> dict[str, Any]:
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dashboards (project_id, name, layout) VALUES (%s, %s, %s) RETURNING id, project_id, name, layout, created_at, updated_at",
                (project_id, name, Json(layout or [])),
            )
            row = cur.fetchone()
        conn.commit()
        return {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "name": row["name"],
            "layout": row["layout"] or [],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }
    finally:
        conn.close()


def dashboard_crud_update(dashboard_id: str, project_id: str, name: Optional[str] = None, layout: Optional[list[Any]] = None) -> Optional[dict[str, Any]]:
    if name is None and layout is None:
        return dashboard_crud_get(dashboard_id, project_id)
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            if name is not None and layout is not None:
                cur.execute(
                    "UPDATE dashboards SET name = %s, layout = %s, updated_at = NOW() WHERE id = %s AND project_id = %s RETURNING id, project_id, name, layout, updated_at",
                    (name, Json(layout), dashboard_id, project_id),
                )
            elif name is not None:
                cur.execute(
                    "UPDATE dashboards SET name = %s, updated_at = NOW() WHERE id = %s AND project_id = %s RETURNING id, project_id, name, layout, updated_at",
                    (name, dashboard_id, project_id),
                )
            else:
                cur.execute(
                    "UPDATE dashboards SET layout = %s, updated_at = NOW() WHERE id = %s AND project_id = %s RETURNING id, project_id, name, layout, updated_at",
                    (Json(layout), dashboard_id, project_id),
                )
            row = cur.fetchone()
        conn.commit()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "name": row["name"],
            "layout": row["layout"] or [],
            "updated_at": str(row["updated_at"]),
        }
    finally:
        conn.close()


def dashboard_crud_delete(dashboard_id: str, project_id: str) -> bool:
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM dashboards WHERE id = %s AND project_id = %s", (dashboard_id, project_id))
            n = cur.rowcount
        conn.commit()
        return n > 0
    finally:
        conn.close()


def execute_widget(project_id: str, insight_type: str, params: dict[str, Any]) -> dict[str, Any]:
    client = get_clickhouse()
    if insight_type == "trend":
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if isinstance(date_from, str):
            date_from = date.fromisoformat(date_from)
        if isinstance(date_to, str):
            date_to = date.fromisoformat(date_to)
        return run_trend(
            client,
            project_id=project_id,
            event=params.get("event", ""),
            date_from=date_from or date.today(),
            date_to=date_to or date.today(),
            interval=params.get("interval", "day"),
        )
    if insight_type == "funnel":
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        if isinstance(date_from, str):
            date_from = date.fromisoformat(date_from)
        if isinstance(date_to, str):
            date_to = date.fromisoformat(date_to)
        return run_funnel(
            client,
            project_id=project_id,
            steps=params.get("steps", []),
            date_from=date_from or date.today(),
            date_to=date_to or date.today(),
        )
    return {"error": "unknown insight_type"}


def get_dashboard_with_results(dashboard_id: str, project_id: str) -> Optional[dict[str, Any]]:
    meta = dashboard_crud_get(dashboard_id, project_id)
    if not meta:
        return None
    layout = meta.get("layout") or []
    widgets = []
    for i, w in enumerate(layout):
        if not isinstance(w, dict):
            continue
        wtype = w.get("type") or "trend"
        params = w.get("params") or {}
        data = execute_widget(project_id, wtype, params)
        widgets.append({"index": i, "type": wtype, "params": params, "data": data})
    return {"dashboard": meta, "widgets": widgets}
