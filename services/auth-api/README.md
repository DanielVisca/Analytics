# Auth API

User registration/login, projects, API keys. Writes only to PostgreSQL (and optional Redis cache).

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Env: `AUTH_POSTGRES_DSN`, `AUTH_JWT_SECRET`.

## Endpoints

- `GET /health`
- `POST /api/register` — body: `{ email, password }`
- `POST /api/login` — form: username (email), password → JWT
- `POST /api/projects` — body: `{ name }` (Bearer JWT)
- `GET /api/projects` — list projects for user
- `POST /api/projects/{project_id}/api-keys` — create API key (returns key once)
- `GET /api/projects/{project_id}/api-keys` — list keys (prefix only)
- `DELETE /api/projects/{project_id}/api-keys/{key_id}` — revoke key
