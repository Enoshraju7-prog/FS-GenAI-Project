"""AI SDK UIMessage ↔ DB row conversion helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.schemas.chat import MessageOut, MessagePartOut, UIMessageIn


def text_from_ui_message(message: UIMessageIn) -> str:
    """Extract plain text from a UIMessage (parts format or content fallback)."""
    if message.parts:
        return "".join(p.text for p in message.parts if p.type == "text")
    return message.content or ""


def extract_last_user_message(messages: list[UIMessageIn]) -> str:
    """Return text of the most recent user message; 422 if none found."""
    for msg in reversed(messages):
        if msg.role == "user":
            return text_from_ui_message(msg)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="No user message found in messages array",
    )


def row_to_message_out(row: dict) -> MessageOut:
    """Convert a chat_messages DB row to the API response shape."""
    return MessageOut(
        id=row["id"],
        role=row["role"],
        parts=[MessagePartOut(type="text", text=row["content"])],
    )
