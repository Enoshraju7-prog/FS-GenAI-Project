"""Print top retrieval hits for client-brief-style questions against the real corpus."""

from __future__ import annotations

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters, format_passages_for_agent

SMOKE_QUERIES: list[tuple[str, SearchFilters | None]] = [
    (
        "What was Apple's total net sales in fiscal 2024?",
        SearchFilters(ticker="AAPL", form="10-K"),
    ),
    (
        "How did NVIDIA describe demand drivers for its Data Center business?",
        SearchFilters(ticker="NVDA", form="10-K"),
    ),
    (
        "What did Alphabet report for EMEA revenues in 2021?",
        SearchFilters(ticker="GOOGL", form="10-K"),
    ),
    (
        "What was Apple's total net sales in fiscal 2024?",
        None,
    ),
]


def main() -> None:
    retriever = DocumentRetriever()
    for query, filters in SMOKE_QUERIES:
        print("\n" + "=" * 80)
        print(f"Query: {query}")
        if filters is not None:
            print(f"Filters: {filters.model_dump_json()}")
        passages = retriever.search(query, filters=filters)
        print(format_passages_for_agent(passages))


if __name__ == "__main__":
    main()
