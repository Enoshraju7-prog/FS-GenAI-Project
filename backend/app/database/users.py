"""Service-role upsert for the users table.

The users table has no INSERT RLS policy — only SELECT/UPDATE — so the
service-role client is required to provision a row on first login.
"""

from __future__ import annotations

from app.auth.dependencies import CurrentUser
from app.database.supabase import get_service_role_client


async def ensure_user(user: CurrentUser) -> None:
    """Upsert the Supabase Auth user into the public users table."""
    client = await get_service_role_client()
    await client.table("users").upsert(
        {"id": str(user.id), "email": user.email}
    ).execute()
