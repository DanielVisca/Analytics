import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import close_clickhouse_pool, get_clickhouse, init_clickhouse_pool
from app.db_pg import close_pg_pool, init_pg_pool
from app.insights import run_funnel, run_trend, run_recent_events
from app.async_jobs import create_and_run_job, get_job
from app import dashboards as dash
from app.auth import get_project_id
from app.logging_config import configure_logging
from app.query_cache import get_cached, set_cached
from app.metrics import (
    FUNNEL_QUERY_LATENCY,
    QUERY_ERRORS,
    REQUESTS_LATENCY,
    REQUESTS_TOTAL,
    TREND_QUERY_LATENCY,
    metrics_endpoint,
    status_class,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        method = request.method
        path = request.url.path or "/"
        response = await call_next(request)
        duration = time.perf_counter() - start
        sc = status_class(response.status_code)
        REQUESTS_TOTAL.labels(method=method, path=path, status_class=sc).inc()
        REQUESTS_LATENCY.labels(method=method, path=path).observe(duration)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_clickhouse_pool()
    init_pg_pool()
    try:
        yield
    finally:
        close_clickhouse_pool()
        close_pg_pool()


app = FastAPI(title="Analytics Query API", lifespan=lifespan)

app.add_middleware(MetricsMiddleware)

# CORS so dashboard at :3000 can call this API; add headers to every response (including 404/5xx)
@app.middleware("http")
async def add_cors_everywhere(request, call_next):
    if request.method == "OPTIONS":
        from starlette.responses import Response
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_route("/metrics", metrics_endpoint, methods=["GET"])


@app.get("/")
async def root():
    return {"service": "Analytics Query API", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/trends")
async def get_trends(
    project_id_from_auth: str = Depends(get_project_id),
    project_id: str = Query("default", alias="project_id"),
    event: str = Query(..., alias="event"),
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    interval: str = Query("day", alias="interval"),
):
    effective_project_id = project_id_from_auth if project_id_from_auth != "default" else project_id
    if interval not in ("day", "week", "month"):
        interval = "day"
    cache_params = {
        "event": event,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "interval": interval,
    }
    cached = get_cached(effective_project_id, "trend", cache_params)
    if cached is not None:
        return cached
    client = get_clickhouse()
    start = time.perf_counter()
    try:
        result = run_trend(client, effective_project_id, event, date_from, date_to, interval)
        TREND_QUERY_LATENCY.observe(time.perf_counter() - start)
        set_cached(effective_project_id, "trend", cache_params, result)
        return result
    except Exception:
        QUERY_ERRORS.labels(query_type="trend").inc()
        TREND_QUERY_LATENCY.observe(time.perf_counter() - start)
        raise


@app.get("/api/events/recent")
async def get_recent_events(
    project_id_from_auth: str = Depends(get_project_id),
    project_id: str = Query("default", alias="project_id"),
    limit: int = Query(50, ge=1, le=500, alias="limit"),
):
    effective_project_id = project_id_from_auth if project_id_from_auth != "default" else project_id
    client = get_clickhouse()
    rows = run_recent_events(client, effective_project_id, limit=limit)
    return {"events": rows}


@app.post("/api/funnels")
async def post_funnels(
    body: dict[str, Any],
    project_id_from_auth: str = Depends(get_project_id),
):
    project_id_body = body.get("project_id") or "default"
    effective_project_id = project_id_from_auth if project_id_from_auth != "default" else project_id_body
    steps = body.get("steps") or []
    date_from = body.get("date_from")
    date_to = body.get("date_to")
    if not steps or not date_from or not date_to:
        return JSONResponse(status_code=400, content={"detail": "project_id, steps, date_from, date_to required"})
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)
    if isinstance(date_to, str):
        date_to = date.fromisoformat(date_to)
    strict = body.get("strict", True)
    conversion_window_days = min(max(1, int(body.get("conversion_window_days", 30))), 365)
    cache_params = {
        "steps": steps,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "strict": strict,
        "conversion_window_days": conversion_window_days,
    }
    cached = get_cached(effective_project_id, "funnel", cache_params)
    if cached is not None:
        return cached
    client = get_clickhouse()
    start = time.perf_counter()
    try:
        result = run_funnel(
            client,
            effective_project_id,
            steps,
            date_from,
            date_to,
            strict=strict,
            conversion_window_days=conversion_window_days,
        )
        FUNNEL_QUERY_LATENCY.observe(time.perf_counter() - start)
        set_cached(effective_project_id, "funnel", cache_params, result)
        return result
    except Exception:
        QUERY_ERRORS.labels(query_type="funnel").inc()
        FUNNEL_QUERY_LATENCY.observe(time.perf_counter() - start)
        raise


@app.post("/api/query/async")
async def run_async_query(
    body: dict[str, Any],
    project_id_from_auth: str = Depends(get_project_id),
):
    project_id_body = body.get("project_id") or "default"
    project_id = project_id_from_auth if project_id_from_auth != "default" else project_id_body
    query_type = body.get("type") or "trend"
    params = body.get("params") or {}
    if query_type == "trend":
        params.setdefault("event", "")
        params.setdefault("date_from", date.today().isoformat())
        params.setdefault("date_to", date.today().isoformat())
        if isinstance(params.get("date_from"), str):
            params["date_from"] = date.fromisoformat(params["date_from"])
        if isinstance(params.get("date_to"), str):
            params["date_to"] = date.fromisoformat(params["date_to"])
    if query_type == "funnel":
        params.setdefault("steps", [])
        if isinstance(params.get("date_from"), str):
            params["date_from"] = date.fromisoformat(params["date_from"])
        if isinstance(params.get("date_to"), str):
            params["date_to"] = date.fromisoformat(params["date_to"])
    job_id = await create_and_run_job(project_id, query_type, params)
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "pending"})


@app.get("/api/query/async/{job_id}")
async def get_async_result(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"detail": "Job not found"})
    if job["status"] == "pending":
        return JSONResponse(status_code=202, content={"job_id": job_id, "status": "pending"})
    if job["status"] == "completed":
        return {"job_id": job_id, "status": "completed", "result": job["result"]}
    return {"job_id": job_id, "status": "failed", "result": job.get("result")}


@app.get("/api/dashboards")
async def list_dashboards(
    project_id_from_auth: str = Depends(get_project_id),
    project_id: str = Query("default", alias="project_id"),
):
    effective_project_id = project_id_from_auth if project_id_from_auth != "default" else project_id
    return dash.dashboard_crud_list(effective_project_id)


@app.post("/api/dashboards")
async def create_dashboard(
    body: dict[str, Any],
    project_id_from_auth: str = Depends(get_project_id),
):
    project_id_body = body.get("project_id") or "default"
    project_id = project_id_from_auth if project_id_from_auth != "default" else project_id_body
    name = body.get("name") or "Unnamed"
    layout = body.get("layout")
    return dash.dashboard_crud_create(project_id, name, layout)


@app.get("/api/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    project_id_from_auth: str = Depends(get_project_id),
    project_id: str = Query("default", alias="project_id"),
    with_results: bool = Query(False, alias="with_results"),
):
    effective_project_id = project_id_from_auth if project_id_from_auth != "default" else project_id
    if with_results:
        out = dash.get_dashboard_with_results(dashboard_id, effective_project_id)
        return out if out else JSONResponse(status_code=404, content={"detail": "Not found"})
    meta = dash.dashboard_crud_get(dashboard_id, effective_project_id)
    return meta if meta else JSONResponse(status_code=404, content={"detail": "Not found"})


@app.patch("/api/dashboards/{dashboard_id}")
async def update_dashboard(
    dashboard_id: str,
    body: dict[str, Any],
    project_id_from_auth: str = Depends(get_project_id),
):
    project_id_body = body.get("project_id") or "default"
    project_id = project_id_from_auth if project_id_from_auth != "default" else project_id_body
    name = body.get("name")
    layout = body.get("layout")
    out = dash.dashboard_crud_update(dashboard_id, project_id, name=name, layout=layout)
    return out if out else JSONResponse(status_code=404, content={"detail": "Not found"})


@app.delete("/api/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    project_id_from_auth: str = Depends(get_project_id),
    project_id: str = Query("default", alias="project_id"),
):
    effective_project_id = project_id_from_auth if project_id_from_auth != "default" else project_id
    ok = dash.dashboard_crud_delete(dashboard_id, effective_project_id)
    return {"deleted": ok} if ok else JSONResponse(status_code=404, content={"detail": "Not found"})
