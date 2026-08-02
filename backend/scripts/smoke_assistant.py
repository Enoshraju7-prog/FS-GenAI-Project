"""Run assistant smoke queries against the real corpus.

Edit QUERIES below, then: uv run python scripts/smoke_assistant.py
"""

from __future__ import annotations

import uuid

from app.assistant.agent import run_document_agent
from app.assistant.deps import DocumentAgentDeps, TurnRegistry
from app.assistant.progress import (
    add_progress_listener,
    clear_progress_listeners,
    elapsed_seconds,
    reset_progress_clock,
)
from app.config import settings
from app.grounding.validator import GroundingValidator, prune_unreferenced_citations
from app.retrieval.retriever import DocumentRetriever

# Edit this list — add, remove, or change questions before each run.
QUERIES = [
    "Across Apple's 2021-2025 10-Ks, how did the revenue mix between iPhone, "
    "Services, Mac, iPad, and Wearables change?",
    "How did NVIDIA describe demand drivers for its Data Center business "
    "from fiscal 2021 through fiscal 2025?",
    "If an analyst asks whether the filings prove that generative AI improved "
    "margins for any of these companies, what evidence exists in the corpus, "
    "and where should the bot refuse to infer beyond the filings?",
    "What is the best stock to buy right now?",
]


def _print_progress(message: str) -> None:
    print(f"[{elapsed_seconds():7.2f}s] {message}", flush=True)


async def _validate(answer, registry):
    return await GroundingValidator().validate(answer, registry)


def main() -> None:
    import asyncio

    clear_progress_listeners()
    add_progress_listener(_print_progress)

    retriever = DocumentRetriever()
    print(f"Model: {settings.openai_chat_model}\n", flush=True)

    for query in QUERIES:
        reset_progress_clock()
        print("\n" + "=" * 80)
        print(f"Query: {query}\n")

        registry = TurnRegistry()
        deps = DocumentAgentDeps(
            retriever=retriever,
            registry=registry,
            thread_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        answer = prune_unreferenced_citations(run_document_agent(query, deps))
        validation = asyncio.run(_validate(answer, registry))

        print(f"insufficient_evidence: {answer.insufficient_evidence}")
        print(f"validation_ok: {validation.ok}")
        if validation.error:
            print(f"validation_error: {validation.error}")
        print(f"\n{answer.answer}\n")

        for citation in answer.citations:
            passage = registry.passages_by_chunk_id.get(citation.chunk_id)
            meta = f"{passage.ticker} {passage.form} p.{passage.page}" if passage else ""
            print(f"[{citation.citation_index}] {meta}")
            print(f"  {citation.excerpt[:200]}")


if __name__ == "__main__":
    main()
