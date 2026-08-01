"""FastAPI dependencies for Supabase JWT authentication."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import acreate_client
from supabase.lib.client_options import AsyncClientOptions
from supabase_auth.errors import AuthApiError

from app.config import settings

# auto_error=False so we can return a proper WWW-Authenticate header ourselves
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    email: str


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Extract the raw Bearer token from the Authorization header."""
    if credentials is None:
        raise _unauthorized()
    return credentials.credentials


async def get_current_user(
    access_token: str = Depends(get_access_token),
) -> CurrentUser:
    """Verify the Supabase JWT and return the authenticated user.

    Raises 401 if the token is invalid or expired.
    Inject with: `user: CurrentUser = Depends(get_current_user)`
    """
    try:
        client = await acreate_client(
            settings.supabase_url,
            settings.supabase_anon_key,
            options=AsyncClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            ),
        )
        response = await client.auth.get_user(access_token)
    except AuthApiError as exc:
        raise _unauthorized(str(exc)) from exc

    if response.user is None:
        raise _unauthorized()

    return CurrentUser(
        id=uuid.UUID(response.user.id),
        email=response.user.email or "",
    )
