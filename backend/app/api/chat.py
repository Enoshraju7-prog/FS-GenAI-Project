"""Chat API — thread CRUD + real grounded-agent streaming endpoint."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import CurrentUser, get_access_token, get_current_user
from app.chat.messages import extract_last_user_message
from app.chat.orchestrator import run_turn
from app.database.chats import (
    create_thread,
    delete_thread,
    list_threads,
    load_messages,
    require_thread_access,
)
from app.database.documents import get_chunk_with_document, get_surrounding_chunks
from app.database.session import get_session
from app.database.supabase import create_user_client
from app.database.users import ensure_user
from app.retrieval.retriever import DocumentRetriever
from app.schemas.chat import (
    ChatStreamRequest,
    ChunkContextPassage,
    ChunkContextResponse,
    CreateThreadRequest,
    ThreadCreated,
    ThreadDetailResponse,
    ThreadsResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])

# One chunk either side is enough to show why a cited passage says what it says without
# turning the panel into a document reader.
CONTEXT_RADIUS = 1


@router.get("/threads", response_model=ThreadsResponse)
async def get_threads(
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> ThreadsResponse:
    threads = await list_threads(user, access_token)
    return ThreadsResponse(threads=threads)


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
    return await create_thread(body.title, user, access_token)


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> ThreadDetailResponse:
    thread = await require_thread_access(thread_id, user)
    messages = await load_messages(thread_id, access_token)
    return ThreadDetailResponse(id=str(thread.id), title=thread.title, messages=messages)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread_route(
    thread_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> None:
    await require_thread_access(thread_id, user)
    await delete_thread(thread_id, access_token)


@router.get("/chunks/{chunk_id}/context", response_model=ChunkContextResponse)
async def get_chunk_context(
    chunk_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> ChunkContextResponse:
    """The cited chunk plus its immediate neighbours, so an excerpt reads in context."""
    return await asyncio.to_thread(_load_chunk_context, chunk_id)


def _load_chunk_context(chunk_id: uuid.UUID) -> ChunkContextResponse:
    with get_session() as session:
        anchor = get_chunk_with_document(session, chunk_id)
        if anchor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

        anchor_chunk, _ = anchor
        passages = [
            ChunkContextPassage(
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                is_anchor=chunk.id == chunk_id,
            )
            for chunk in [anchor_chunk, *get_surrounding_chunks(session, chunk_id, CONTEXT_RADIUS)]
        ]
        passages.sort(key=lambda p: p.chunk_index)
        return ChunkContextResponse(passages=passages)


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user: CurrentUser = Depends(get_current_user),
    access_token: str = Depends(get_access_token),
) -> StreamingResponse:
    await ensure_user(user)
    thread = await require_thread_access(body.thread_id, user)
    user_message = extract_last_user_message(body.messages)
    client = await create_user_client(access_token)
    retriever = DocumentRetriever()

    return StreamingResponse(
        run_turn(
            client=client,
            thread_id=body.thread_id,
            user=user,
            user_message=user_message,
            thread_title=thread.title,
            retriever=retriever,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
