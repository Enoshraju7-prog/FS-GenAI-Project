# Data

Local data artifacts for development live here.

- `downloads/` holds raw source files fetched from SEC EDGAR, grouped by year.
- `markdown/` holds Docling-converted Markdown extracts, mirroring the same year folders + manifest.
- Both are gitignored because the corpus (and its derived files) can get large.
- Fetch a sample corpus with `uv run data/download.py`
- Convert it to Markdown with the backend venv active: `python data/convert_to_markdown.py`
