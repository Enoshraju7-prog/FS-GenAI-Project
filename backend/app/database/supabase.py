"""Supabase client construction for server-side database and auth access."""

from supabase import AsyncClient, acreate_client
from supabase.lib.client_options import AsyncClientOptions

from app.config import settings

_service_role_client: AsyncClient | None = None


def _server_client_options(
    *,
    access_token: str | None = None,
) -> AsyncClientOptions:
    headers: dict[str, str] = {}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"

    return AsyncClientOptions(
        headers=headers,
        auto_refresh_token=False,
        persist_session=False,
    )


async def create_user_client(access_token: str) -> AsyncClient:
    """Fresh per-request client using the anon key + user JWT.

    RLS policies evaluate auth.uid() from the Bearer token, so the user
    only sees rows they own.
    """
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=_server_client_options(access_token=access_token),
    )


async def get_service_role_client() -> AsyncClient:
    """Singleton service-role client — bypasses RLS entirely.

    Use only for ingestion scripts and admin operations, never in
    user-facing request handlers.
    """
    global _service_role_client
    if _service_role_client is None:
        _service_role_client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
            options=_server_client_options(),
        )
    return _service_role_client
