"""Client for validating API keys via Auth API."""
from typing import Optional

import httpx

from app.config import settings


async def validate_api_key(api_key: str) -> Optional[str]:
    """Validate API key with Auth API. Returns project_id if valid, None otherwise."""
    url = f"{settings.auth_api_url.rstrip('/')}/api/internal/validate-key"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url, headers={"X-API-Key": api_key})
            if r.status_code == 200:
                data = r.json()
                return data.get("project_id")
            return None
    except Exception:
        return None
