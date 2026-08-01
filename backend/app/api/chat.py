"""Chat API — thread CRUD + streaming endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import CurrentUser, get_access_token, get_current_user
from app.chat.messages import extract_last_user_message, row_to_message_out
from app.chat.streaming import STUB_REPLY, stub_stream
from app.database.chats import (
    append_messages,
    create_thread,
    get_thread_messages,
    list_threads,
    require_thread_access,
    update_thread_title,
)
from app.database.users import ensure_user
from app.schemas.chat import (
    ChatStreamRequest,
    CreateThreadRequest,
    MessageOut,
    ThreadCreated,
    ThreadDetailResponse,
    ThreadsResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/threads", response_model=ThreadsResponse)
async def get_threads(
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> ThreadsResponse:
    rows = await list_threads(user, access_token)
    return ThreadsResponse(threads=rows)


@router.post(
    "/threads",
    response_model=ThreadCreated,
    status_code=status.HTTP_201_CREATED,
)
async def post_thread(
    body: CreateThreadRequest,
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> ThreadCreated:
    await ensure_user(user)
    row = await create_thread(body.title, user, access_token)
    return ThreadCreated(**row)


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: str,
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> ThreadDetailResponse:
    import uuid as _uuid

    tid = _uuid.UUID(thread_id)
    thread = await require_thread_access(tid, user)
    rows = await get_thread_messages(tid, access_token)
    messages: list[MessageOut] = [row_to_message_out(r) for r in rows]
    return ThreadDetailResponse(
        id=thread["id"],
        title=thread["title"],
        messages=messages,
    )


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> StreamingResponse:
    await ensure_user(user)
    thread = await require_thread_access(body.thread_id, user)

    user_text = extract_last_user_message(body.messages)

    await append_messages(body.thread_id, user_text, STUB_REPLY)

    # Auto-title: update thread title from first user message
    if thread["title"] == "New chat":
        title = user_text[:60].strip() or "New chat"
        await update_thread_title(body.thread_id, title)

    return StreamingResponse(
        stub_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
