"""SSE stub stream generator — AI SDK v7 UIMessage stream protocol.

Wire format: text/event-stream with JSON payloads.
  data: {"type":"start"}\n\n
  data: {"type":"start-step"}\n\n
  data: {"type":"text-start","id":"text-1"}\n\n
  data: {"type":"text-delta","id":"text-1","delta":"word "}\n\n
  ...
  data: {"type":"text-end","id":"text-1"}\n\n
  data: {"type":"finish-step"}\n\n
  data: {"type":"finish"}\n\n
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

STUB_REPLY = "This is a stubbed response. Real RAG answers arrive in Phase 6."

_TEXT_ID = "text-1"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def stub_stream() -> AsyncGenerator[str, None]:
    yield _sse({"type": "start"})
    yield _sse({"type": "start-step"})
    yield _sse({"type": "text-start", "id": _TEXT_ID})

    words = STUB_REPLY.split(" ")
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield _sse({"type": "text-delta", "id": _TEXT_ID, "delta": chunk})
        await asyncio.sleep(0.05)

    yield _sse({"type": "text-end", "id": _TEXT_ID})
    yield _sse({"type": "finish-step"})
    yield _sse({"type": "finish"})
