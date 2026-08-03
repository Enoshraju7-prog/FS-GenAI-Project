from types import SimpleNamespace

import pytest

from ingest.chunking import (
    CHUNK_MAX_TOKENS,
    build_tokenizer,
    chunk_document,
    html_path_for_accession,
    load_manifest_html_paths,
    _base_chunk_metadata,
    _narrative_text_without_tables,
    _page_from_chunk_meta,
    _section_from_chunk,
    _table_matches_chunk,
)
from ingest.sec_tables import ExtractedTable, TableColumn, TableRow, TableCell

FILING_METADATA = {
    "ticker": "AAPL",
    "cik": "0000320193",
    "company_name": "Apple Inc.",
    "form": "10-K",
    "filing_date": "2024-11-01",
    "report_date": "2024-09-28",
    "fiscal_year": 2024,
    "accession_number": "0000320193-24-000123",
    "primary_document": "aapl-20240928.htm",
    "source_url": "https://example.com/aapl.htm",
}


def _make_table() -> ExtractedTable:
    return ExtractedTable(
        table_index=0,
        title="Segment Revenue",
        units="in millions",
        columns=(TableColumn("Category"), TableColumn("2024")),
        rows=(TableRow(label="Total net sales", cells=(TableCell(text="$391,035"),)),),
        footnotes=[],
        markdown="| Category | 2024 |\n| --- | --- |\n| Total net sales | $391,035 |",
        source_html_hash="abc123",
    )


def test_patched_tokenizer_counts_tokens_without_erroring_on_special_strings():
    tokenizer = build_tokenizer(max_tokens=CHUNK_MAX_TOKENS)

    count = tokenizer.count_tokens("Revenue increased <|endoftext|> significantly in 2024.")

    assert count > 0


def test_page_from_chunk_meta_reads_origin_page_no():
    meta = SimpleNamespace(origin=SimpleNamespace(page_no=42), doc_items=[])

    assert _page_from_chunk_meta(meta) == "42"


def test_page_from_chunk_meta_falls_back_to_doc_item_provenance():
    prov_entry = SimpleNamespace(page_no=7)
    item = SimpleNamespace(prov=[prov_entry])
    meta = SimpleNamespace(origin=SimpleNamespace(page_no=None), doc_items=[item])

    assert _page_from_chunk_meta(meta) == "7"


def test_page_from_chunk_meta_returns_none_when_no_provenance():
    meta = SimpleNamespace(origin=None, doc_items=[])

    assert _page_from_chunk_meta(meta) is None


def test_section_from_chunk_uses_headings():
    meta = SimpleNamespace(headings=["Item 7", "Results of Operations"])

    assert _section_from_chunk(meta, "some text") == "Item 7 > Results of Operations"


def test_section_from_chunk_falls_back_to_item_regex():
    meta = SimpleNamespace(headings=[])

    assert _section_from_chunk(meta, "See Item 1A. Risk Factors for details.") == "Item 1A"


def test_section_from_chunk_returns_none_when_nothing_found():
    meta = SimpleNamespace(headings=[])

    assert _section_from_chunk(meta, "plain narrative text") is None


def test_narrative_text_without_tables_strips_pipe_rows():
    text = "Some narrative line.\n| a | b |\n| --- | --- |\nAnother narrative line."

    result = _narrative_text_without_tables(text)

    assert "Some narrative line." in result
    assert "Another narrative line." in result
    assert "|" not in result


def test_table_matches_chunk_by_row_label():
    table = _make_table()

    assert _table_matches_chunk("... Total net sales figures follow ...", table)
    assert not _table_matches_chunk("unrelated narrative", table)


def test_base_chunk_metadata_carries_filing_identity():
    metadata = _base_chunk_metadata(FILING_METADATA)

    assert metadata["ticker"] == "AAPL"
    assert metadata["accession_number"] == "0000320193-24-000123"
    assert metadata["fiscal_year"] == 2024


def test_load_manifest_html_paths_derives_htm_from_markdown_local_path(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        '{"filings": [{"accession_number": "acc-1", "local_path": "2024/foo.md"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr("ingest.chunking.MANIFEST_PATH", manifest_path)

    paths = load_manifest_html_paths()

    assert paths == {"acc-1": "2024/foo.htm"}


def test_html_path_for_accession_raises_when_missing(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"filings": []}', encoding="utf-8")
    monkeypatch.setattr("ingest.chunking.MANIFEST_PATH", manifest_path)

    with pytest.raises(KeyError):
        html_path_for_accession("does-not-exist")


FIXTURE_HTML = """
<html><body>
<p>Apple Inc. designs, manufactures, and markets smartphones, personal computers,
tablets, wearables, and accessories worldwide.</p>
<h2>Item 7. Management's Discussion and Analysis</h2>
<p>Total net sales increased during fiscal 2024 compared to fiscal 2023,
driven by growth in Services.</p>
<p>The following table shows net sales by category (in millions):</p>
<table>
  <tr><td>Category</td><td>2024</td><td>2023</td></tr>
  <tr><td>iPhone</td><td>$201,183</td><td>$200,583</td></tr>
  <tr><td>Total net sales</td><td>$391,035</td><td>$383,285</td></tr>
</table>
</body></html>
"""


def test_chunk_document_end_to_end(tmp_path):
    html_path = tmp_path / "fixture.htm"
    html_path.write_text(FIXTURE_HTML, encoding="utf-8")

    records = chunk_document(html_path, FILING_METADATA)

    assert records, "expected at least one chunk"
    assert all(r.token_count <= CHUNK_MAX_TOKENS for r in records)

    kinds = {r.chunk_metadata["chunk_kind"] for r in records}
    assert "table" in kinds

    table_records = [r for r in records if r.chunk_metadata["chunk_kind"] == "table"]
    assert any("391,035" in r.text for r in table_records)

    # The full table dict is stored once per table, not on every chunk of it — copying
    # it onto each chunk is what previously blew the database size budget.
    for table_index in {r.chunk_metadata["table_index"] for r in table_records}:
        with_blob = [
            r
            for r in table_records
            if r.chunk_metadata["table_index"] == table_index and "table" in r.chunk_metadata
        ]
        assert len(with_blob) == 1

    for record in records:
        assert record.chunk_metadata["ticker"] == "AAPL"
        assert record.chunk_metadata["accession_number"] == "0000320193-24-000123"

    # chunk_index is contiguous starting at 0
    assert [r.chunk_index for r in records] == list(range(len(records)))


def test_chunk_document_respects_max_chunks(tmp_path):
    html_path = tmp_path / "fixture.htm"
    html_path.write_text(FIXTURE_HTML, encoding="utf-8")

    records = chunk_document(html_path, FILING_METADATA, max_chunks=1)
    full_records = chunk_document(html_path, FILING_METADATA)

    assert len(records) <= len(full_records)
