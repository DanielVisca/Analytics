from typing import Optional
from uuid import UUID

import psycopg2
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm

from app.config import settings
from app.db import get_conn
from app.models import UserCreate, UserResponse, ProjectCreate, ProjectResponse, ApiKeyCreate, ApiKeyResponse
from app.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    hash_api_key,
    key_prefix,
    generate_api_key,
)

app = FastAPI(title="Analytics Auth API")
security = HTTPBearer(auto_error=False)


def get_current_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/register", response_model=UserResponse)
async def register(body: UserCreate):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email",
                (body.email, hash_password(body.password)),
            )
            row = cur.fetchone()
        conn.commit()
        return {"id": str(row["id"]), "email": row["email"]}
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        conn.close()


@app.post("/api/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM users WHERE email = %s",
                (form.username,),
            )
            row = cur.fetchone()
        if not row or not verify_password(form.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(str(row["id"]))
        return {"access_token": token, "token_type": "bearer"}
    finally:
        conn.close()


@app.post("/api/projects", response_model=ProjectResponse)
async def create_project(body: ProjectCreate, user_id: str = Depends(get_current_user_id)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO projects (name) VALUES (%s) RETURNING id, name",
                (body.name,),
            )
            row = cur.fetchone()
            project_id = row["id"]
            cur.execute(
                "INSERT INTO project_members (project_id, user_id, role) VALUES (%s, %s, 'admin')",
                (project_id, user_id),
            )
        conn.commit()
        return {"id": str(project_id), "name": row["name"]}
    finally:
        conn.close()


@app.get("/api/projects", response_model=list[ProjectResponse])
async def list_projects(user_id: str = Depends(get_current_user_id)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT p.id, p.name FROM projects p JOIN project_members pm ON p.id = pm.project_id WHERE pm.user_id = %s",
                (user_id,),
            )
            rows = cur.fetchall()
        return [{"id": str(r["id"]), "name": r["name"]} for r in rows]
    finally:
        conn.close()


@app.post("/api/projects/{project_id}/api-keys", response_model=dict)
async def create_api_key(
    project_id: UUID,
    body: ApiKeyCreate = None,
    user_id: str = Depends(get_current_user_id),
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
                (str(project_id), user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
            key = generate_api_key()
            key_hash = hash_api_key(key)
            prefix = key_prefix(key)
            name = (body and body.name) or None
            cur.execute(
                "INSERT INTO api_keys (project_id, key_hash, key_prefix, name) VALUES (%s, %s, %s, %s) RETURNING id, key_prefix, name, created_at",
                (str(project_id), key_hash, prefix, name),
            )
            row = cur.fetchone()
        conn.commit()
        return {
            "id": str(row["id"]),
            "key_prefix": row["key_prefix"],
            "name": row["name"],
            "created_at": str(row["created_at"]),
            "api_key": key,
        }
    finally:
        conn.close()


@app.get("/api/projects/{project_id}/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(project_id: UUID, user_id: str = Depends(get_current_user_id)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
                (str(project_id), user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
            cur.execute(
                "SELECT id, key_prefix, name, created_at FROM api_keys WHERE project_id = %s",
                (str(project_id),),
            )
            rows = cur.fetchall()
        return [
            {"id": str(r["id"]), "key_prefix": r["key_prefix"], "name": r["name"], "created_at": str(r["created_at"])}
            for r in rows
        ]
    finally:
        conn.close()


@app.delete("/api/projects/{project_id}/api-keys/{key_id}")
async def revoke_api_key(
    project_id: UUID,
    key_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
                (str(project_id), user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
            cur.execute(
                "DELETE FROM api_keys WHERE id = %s AND project_id = %s",
                (str(key_id), str(project_id)),
            )
        conn.commit()
        return {"status": "revoked"}
    finally:
        conn.close()
