# Document Copilot — Backend

FastAPI service powering the Document Copilot RAG application.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
# Install dependencies and create .venv
uv sync

# Copy and fill in environment variables
cp .env.example .env
```

## Running the dev server

```bash
uv run uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000`  
Docs (Swagger UI) at `http://127.0.0.1:8000/docs`  
Health check at `http://127.0.0.1:8000/health`

## Database migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "description"
```

## Running tests

```bash
# Fast unit tests only (no network/DB)
uv run pytest -m "not integration"

# All tests (requires live Supabase + OpenAI credentials)
uv run pytest
```

## Linting

```bash
uv run ruff check .
uv run ruff format .
```
