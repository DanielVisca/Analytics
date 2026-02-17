from datetime import date
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import get_clickhouse
from app.insights import run_funnel, run_trend
from app.async_jobs import create_and_run_job, get_job
from app import dashboards as dash

app = FastAPI(title="Analytics Query API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/trends")
async def get_trends(
    project_id: str = Query(..., alias="project_id"),
    event: str = Query(..., alias="event"),
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    interval: str = Query("day", alias="interval"),
):
    if interval not in ("day", "week", "month"):
        interval = "day"
    client = get_clickhouse()
    result = run_trend(client, project_id, event, date_from, date_to, interval)
    return result


@app.post("/api/funnels")
async def post_funnels(
    body: dict[str, Any],
):
    project_id = body.get("project_id") or "default"
    steps = body.get("steps") or []
    date_from = body.get("date_from")
    date_to = body.get("date_to")
    if not steps or not date_from or not date_to:
        return JSONResponse(status_code=400, content={"detail": "project_id, steps, date_from, date_to required"})
    if isinstance(date_from, str):
        date_from = date.fromisoformat(date_from)
    if isinstance(date_to, str):
        date_to = date.fromisoformat(date_to)
    client = get_clickhouse()
    result = run_funnel(client, project_id, steps, date_from, date_to)
    return result


@app.post("/api/query/async")
async def run_async_query(body: dict[str, Any]):
    project_id = body.get("project_id") or "default"
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
async def list_dashboards(project_id: str = Query(..., alias="project_id")):
    return dash.dashboard_crud_list(project_id)


@app.post("/api/dashboards")
async def create_dashboard(body: dict[str, Any]):
    project_id = body.get("project_id") or "default"
    name = body.get("name") or "Unnamed"
    layout = body.get("layout")
    return dash.dashboard_crud_create(project_id, name, layout)


@app.get("/api/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    project_id: str = Query(..., alias="project_id"),
    with_results: bool = Query(False, alias="with_results"),
):
    if with_results:
        out = dash.get_dashboard_with_results(dashboard_id, project_id)
        return out if out else JSONResponse(status_code=404, content={"detail": "Not found"})
    meta = dash.dashboard_crud_get(dashboard_id, project_id)
    return meta if meta else JSONResponse(status_code=404, content={"detail": "Not found"})


@app.patch("/api/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: str, body: dict[str, Any]):
    project_id = body.get("project_id") or "default"
    name = body.get("name")
    layout = body.get("layout")
    out = dash.dashboard_crud_update(dashboard_id, project_id, name=name, layout=layout)
    return out if out else JSONResponse(status_code=404, content={"detail": "Not found"})


@app.delete("/api/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: str, project_id: str = Query(..., alias="project_id")):
    ok = dash.dashboard_crud_delete(dashboard_id, project_id)
    return {"deleted": ok} if ok else JSONResponse(status_code=404, content={"detail": "Not found"})
