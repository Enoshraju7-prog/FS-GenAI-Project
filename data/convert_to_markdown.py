# /// script
# requires-python = ">=3.12"
# ///
"""Convert downloaded SEC filings (HTML) into Markdown for later chunking/ingestion.

Uses docling (https://github.com/docling-project/docling), installed as a backend
dev dependency, so run this with the backend virtualenv:

    source backend/.venv/bin/activate
    python data/convert_to_markdown.py
"""
from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from docling.document_converter import DocumentConverter

# Params: edit these, then run the script
INPUT_DIR = Path(__file__).resolve().parent / "downloads"
OUTPUT_DIR = Path(__file__).resolve().parent / "markdown"
MANIFEST_PATH = INPUT_DIR / "manifest.json"
CLEAR_OUTPUT_DIR = False
SKIP_EXISTING = True


def convert_downloads_to_markdown() -> dict:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Missing {MANIFEST_PATH}. Run `uv run data/download.py` first."
        )
    source_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    filings = source_manifest.get("filings", [])
    if not filings:
        raise ValueError(f"No filings listed in {MANIFEST_PATH}")

    if CLEAR_OUTPUT_DIR and OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    manifest = {
        "source": source_manifest.get("source", "SEC EDGAR"),
        "converted_at_utc": datetime.now(UTC).isoformat(),
        "form": source_manifest.get("form", "10-K"),
        "converted_count": 0,
        "filings": [],
    }

    for filing in filings:
        source_path = INPUT_DIR / filing["local_path"]
        markdown_relative_path = Path(filing["local_path"]).with_suffix(".md")
        markdown_path = OUTPUT_DIR / markdown_relative_path

        if SKIP_EXISTING and markdown_path.is_file():
            print(f"Skipping {filing['local_path']} (already converted)")
        else:
            print(f"Converting {filing['local_path']}...")
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            result = converter.convert(source_path)
            markdown_path.write_text(
                result.document.export_to_markdown(), encoding="utf-8"
            )

        manifest["filings"].append(
            {**filing, "local_path": str(markdown_relative_path)}
        )
        manifest["converted_count"] += 1

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = convert_downloads_to_markdown()
    print(f"Converted {result['converted_count']} filing(s) to {OUTPUT_DIR}")
    print(f"Manifest: {OUTPUT_DIR / 'manifest.json'}")
