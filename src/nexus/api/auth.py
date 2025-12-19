"""
Authentication middleware.

API key based authentication for Nexus API.
"""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

# API key can be passed via header or query parameter
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


def get_api_key(request: Request) -> str:
    """Get configured API key from app state."""
    return request.app.state.api_key


async def verify_api_key(
    request: Request,
    api_key_header: str | None = Security(api_key_header),
    api_key_query: str | None = Security(api_key_query),
) -> str:
    """
    Verify API key from header or query parameter.

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Check if auth is enabled
    config = request.app.state.config
    if not config.server.auth_enabled:
        return "no-auth"

    # Get provided key
    provided_key = api_key_header or api_key_query

    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Get expected key
    expected_key = get_api_key(request)

    # Constant-time comparison
    if not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return provided_key


# Dependency for protected routes
require_auth = Depends(verify_api_key)

