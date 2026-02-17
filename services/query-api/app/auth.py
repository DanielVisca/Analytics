from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer

# Optional API key (v1: can skip auth for local dev)
APIKeyHeaderAuth = APIKeyHeader(name="X-API-Key", auto_error=False)
BearerAuth = HTTPBearer(auto_error=False)


async def get_optional_project_id(
    x_api_key: Annotated[str | None, Depends(APIKeyHeaderAuth)],
) -> str | None:
    """Resolve project_id from API key if present. For v1 we accept missing key and use default."""
    if not x_api_key or not x_api_key.strip():
        return "default"
    # In v1 we do not validate against DB here; Auth API will. For Query API we just pass through.
    return "default"
