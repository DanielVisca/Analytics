from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer

from app.auth_client import validate_api_key
from app.config import settings

APIKeyHeaderAuth = APIKeyHeader(name="X-API-Key", auto_error=False)
BearerAuth = HTTPBearer(auto_error=False)


async def get_project_id(
    x_api_key: Annotated[str | None, Depends(APIKeyHeaderAuth)],
) -> str:
    """Resolve project_id from API key. When require_api_key is True, missing/invalid key returns 401."""
    if not x_api_key or not x_api_key.strip():
        if settings.require_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
            )
        return "default"
    project_id = await validate_api_key(x_api_key.strip())
    if project_id is None:
        if settings.require_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return "default"
    return project_id
