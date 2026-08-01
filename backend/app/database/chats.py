"""Supabase client DB helpers for threads and messages.

Uses the user-scoped client (respects RLS) for list/create/read.
Uses the service-role client to distinguish 404 (missing) from 403 (wrong owner),
because RLS alone returns empty rows for foreign threads.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.auth.dependencies import CurrentUser
from app.database.supabase import create_user_client, get_service_role_client


async def list_threads(user: CurrentUser, access_token: str) -> list[dict]:
    client = await create_user_client(access_token)
    response = await (
        client.table("chat_threads")
        .select("id,title,user_id,created_at,updated_at")
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def create_thread(title: str, user: CurrentUser, access_token: str) -> dict:
    client = await create_user_client(access_token)
    response = await (
        client.table("chat_threads")
        .insert({"id": str(uuid.uuid4()), "user_id": str(user.id), "title": title})
        .execute()
    )
    return response.data[0]


async def require_thread_access(thread_id: uuid.UUID, user: CurrentUser) -> dict:
    """Fetch thread via service role; raise 404 if missing, 403 if wrong owner."""
    service_client = await get_service_role_client()
    response = await (
        service_client.table("chat_threads")
        .select("id,user_id,title,created_at,updated_at")
        .eq("id", str(thread_id))
        .maybe_single()
        .execute()
    )
    if response.data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if response.data["user_id"] != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return response.data


async def get_thread_messages(thread_id: uuid.UUID, access_token: str) -> list[dict]:
    client = await create_user_client(access_token)
    response = await (
        client.table("chat_messages")
        .select("id,thread_id,role,content,created_at")
        .eq("thread_id", str(thread_id))
        .order("created_at")
        .execute()
    )
    return response.data


async def append_messages(
    thread_id: uuid.UUID,
    user_content: str,
    assistant_content: str,
) -> None:
    service_client = await get_service_role_client()
    await (
        service_client.table("chat_messages")
        .insert([
            {
                "id": str(uuid.uuid4()),
                "thread_id": str(thread_id),
                "role": "user",
                "content": user_content,
            },
            {
                "id": str(uuid.uuid4()),
                "thread_id": str(thread_id),
                "role": "assistant",
                "content": assistant_content,
            },
        ])
        .execute()
    )


async def update_thread_title(thread_id: uuid.UUID, title: str) -> None:
    service_client = await get_service_role_client()
    await (
        service_client.table("chat_threads")
        .update({"title": title})
        .eq("id", str(thread_id))
        .execute()
    )
