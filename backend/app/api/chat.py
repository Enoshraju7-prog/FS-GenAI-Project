from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user
from app.database.models.chat_messages import ChatMessage
from app.database.models.chat_threads import ChatThread
from app.database.models.message_role import MessageRole
from app.database.session import get_session

router = APIRouter(prefix="/chat", tags=["chat"])

_STUB_REPLY = "This is a stubbed response. Real RAG answers arrive in Phase 6."


class IncomingMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    threadId: uuid.UUID
    messages: list[IncomingMessage]


async def _stream_text(text: str) -> AsyncGenerator[str, None]:
    """Yield Vercel AI SDK data-stream protocol chunks."""
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield f"0:{json.dumps(chunk)}\n"
        await asyncio.sleep(0.04)
    yield 'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    thread = await session.get(ChatThread, body.threadId)
    if thread is None or thread.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    user_content = body.messages[-1].content if body.messages else ""

    session.add(ChatMessage(thread_id=body.threadId, role=MessageRole.user, content=user_content))
    session.add(ChatMessage(thread_id=body.threadId, role=MessageRole.assistant, content=_STUB_REPLY))
    await session.commit()

    return StreamingResponse(
        _stream_text(_STUB_REPLY),
        media_type="text/plain",
        headers={"X-Vercel-AI-Data-Stream": "v1"},
    )
