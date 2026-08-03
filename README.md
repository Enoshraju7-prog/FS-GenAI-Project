# Document Copilot

An AI-powered chat app that lets financial analysts ask plain-English questions about SEC 10-K filings and get answers grounded in cited source passages — built on FastAPI, React, Supabase, and OpenAI.

---

## What it does

Investment analysts at **Driftwood Capital** (a fictional firm) currently read through hundreds of pages of annual reports manually before they can do any original analysis. Document Copilot replaces that intake work: an analyst types a question like *"What were Apple's R&D expenses in fiscal 2024?"* and gets a direct answer with an exact quote from the relevant filing.

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Backend API | Python + FastAPI | Fast, async, type-safe API framework |
| Frontend | React + Vite + TypeScript | Single-page app, fast dev server |
| Styling | Tailwind CSS + shadcn/ui | Utility CSS + pre-built accessible components |
| Database | Supabase Postgres | Hosted Postgres with auth, Row Level Security, and vector search built in |
| Schema migrations | SQLAlchemy + Alembic | Define tables in Python, apply changes safely with migration files |
| Auth | Supabase Auth (email) | JWT-based login without building your own auth server |
| Vector search | pgvector (Supabase) | Semantic similarity search stored right in the database |
| LLM + embeddings | OpenAI | GPT for answers, `text-embedding-3-small` for vector embeddings |
| Hosting | Railway | Simple deploy for both the Python backend and React frontend |

---

## Repo layout

```
document-copilot/
├── CLAUDE.md              # Instructions for AI coding agents
├── README.md              # This file
├── data/                  # Download script + local SEC filing corpus (files gitignored)
├── docs/                  # Specs, guides, architecture notes
│   ├── client-brief.md    # What Driftwood needs + 10 example questions
│   ├── architecture.md    # System design and data model
│   └── todos.md           # Phase-by-phase build checklist
├── backend/               # Python FastAPI service
│   ├── app/
│   │   ├── main.py        # App entry point, CORS, router registration
│   │   ├── config.py      # All env-var settings in one place
│   │   ├── api/           # HTTP route handlers
│   │   ├── auth/          # JWT verification + current-user dependency
│   │   ├── chat/          # Message conversion, orchestrator, SSE streaming
│   │   ├── retrieval/     # Hybrid search: pgvector + full-text + RRF fusion (see its README.md)
│   │   ├── assistant/     # PydanticAI agent, tools, grounded output (see its README.md)
│   │   ├── grounding/     # Citation validation — fails closed if any claim is unsupported
│   │   ├── database/      # Supabase client, DB query helpers, ORM models
│   │   └── schemas/       # Pydantic request/response models
│   ├── scripts/           # Editable smoke-test scripts (real corpus, no test framework)
│   ├── alembic/           # Database migration files
│   └── pyproject.toml     # Python dependencies
└── frontend/              # React SPA
    └── src/
        ├── App.tsx            # Router
        ├── pages/             # Full-page components (login, chat layout)
        ├── components/        # Reusable UI components
        └── lib/               # API helpers, Supabase client, env validation
```

---

## Prerequisites

Install these tools before setting up the project:

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ (LTS) | [nodejs.org](https://nodejs.org/) |
| pnpm | latest | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need a **Supabase project** and an **OpenAI API key**. See the setup guides below.

---

## Running locally

### 1. Clone the repo

```bash
git clone https://github.com/Enoshraju7-prog/FS-GenAI-Project.git
cd FS-GenAI-Project
git checkout development
```

### 2. Set up Supabase

Follow [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) to create a Supabase project and collect your credentials.

### 3. Backend

```bash
cd backend

# Create the .env file (copy and fill in your values)
cp .env.example .env

# Install dependencies (add --extra ingest if you plan to run the ingestion pipeline —
# it pulls Docling, which is large and only needed to parse SEC HTML locally)
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the API server (runs on http://localhost:8000)
uv run uvicorn app.main:app --reload
```

Your `.env` needs these values:
```
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
DATABASE_URL=postgresql://postgres:password@db.yourproject.supabase.co:5432/postgres
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:5173

# Optional — shown with their defaults
LOG_LEVEL=INFO       # DEBUG | INFO | WARNING | ERROR
LOG_JSON=false       # true for machine-readable logs when deployed
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

`DATABASE_URL` must be the **direct/session** connection string, not the transaction
pooler — Alembic and pgvector queries need a session connection.

See `backend/.env.example` for the full annotated list, including retrieval tuning.

Verify it's running: visit `http://localhost:8000/health` — you should see `{"status":"ok"}`.

### 4. Frontend

```bash
cd frontend

# Create the .env file
cp .env.example .env.local

# Install dependencies
pnpm install

# Start the dev server (runs on http://localhost:5173)
pnpm dev
```

Your `.env.local` needs:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://yourproject.supabase.co
VITE_SUPABASE_ANON_KEY=...
```

### 5. Download sample data (optional — needed for Phase 4+)

```bash
# Edit USER_AGENT at the top of data/download.py first
uv run data/download.py
```

This downloads 10-K filings for AAPL, MSFT, NVDA, AMZN, GOOGL into `data/downloads/`.

### 6. Try the retrieval + assistant pipeline directly (optional)

Once the corpus is ingested (Phase 4), you can query it without the frontend:

```bash
cd backend
uv run python -m scripts.smoke_retrieval    # raw hybrid search results
uv run python -m scripts.smoke_assistant    # full agent: search -> cite -> validate
```

Edit `QUERY_KEY` at the top of `smoke_assistant.py` to try a different question. See
[`backend/app/retrieval/README.md`](backend/app/retrieval/README.md) and
[`backend/app/assistant/README.md`](backend/app/assistant/README.md) for how each pipeline works.

---

## Build progress

| Phase | Status | What gets built |
|---|---|---|
| 0 — Prerequisites | ✅ Done | Toolchain, Supabase project, sample SEC corpus |
| 1 — Backend scaffold | ✅ Done | FastAPI app, Supabase schema + migrations, health check |
| 2 — Auth | ✅ Done | Supabase JWT login, protected routes on backend + frontend |
| 3 — Chat shell | ✅ Done | Thread CRUD, streaming stub response, chat UI with sidebar |
| 4 — Ingestion | ✅ Done | Parse SEC filings → hierarchical chunks → OpenAI embeddings → Supabase |
| 5 — Retrieval | ✅ Done | Vector (pgvector) + full-text search with LLM keyword extraction, fused with Reciprocal Rank Fusion |
| 6 — LLM agent | ✅ Done | PydanticAI agent, grounded answers, fail-closed citation validation |
| 7 — Trust UI | ✅ Done | Citation chips, source panel with neighbouring chunks, markdown tables, live pipeline status, light/dark mode |
| 8 — Pilot readiness | ✅ Done | `structlog`, all 10 brief questions grounded, DB pool sizing, table-fidelity fix (19,544 → 6,051 chunks) |
| 9 — Deploy (Railway) | ✅ Done | Two Docker services on Railway, Caddy serving the SPA — see [Deployment](#deployment-railway) |

---

## Deployment (Railway)

The app runs as **two Railway services in one project**, both built from Dockerfiles.
Supabase stays at Supabase — there is no Railway Postgres.

| Service | Built from | Runs |
|---|---|---|
| `document-copilot-backend` | `backend/Dockerfile` | FastAPI + Uvicorn |
| `document-copilot-frontend` | `frontend/Dockerfile` | Vite build served by Caddy |

**Live:** https://document-copilot-frontend-production-85f8.up.railway.app

Three things that are easy to get wrong, and why they matter:

- **This is a monorepo.** There is no `package.json` or `pyproject.toml` at the repo
  root, so a builder pointed at the root cannot tell what the project is. Each service
  builds from its own subdirectory (`railway up ./backend --path-as-root`).
- **`VITE_*` variables are build-time, not runtime.** Vite bakes them into the
  JavaScript bundle, so they must be set *before* the frontend image is built —
  a runtime variable arrives far too late. They are declared as `ARG` in
  `frontend/Dockerfile`.
- **Deploy the backend first.** The frontend build needs the backend's public URL, and
  the backend then needs the frontend's URL in `ALLOWED_ORIGINS` for CORS. Order is:
  backend → domain → frontend → domain → update backend CORS.

After deploying, set **Supabase → Authentication → URL Configuration** to the frontend
domain. Password sign-in works without it, but sign-up confirmation and password-reset
emails would link to `localhost`.

Health endpoints: backend `/health` returns `{"status":"ok"}`, frontend `/health`
returns `ok`.

---

## Key concepts for interviews

**RAG (Retrieval-Augmented Generation)** — Instead of asking a language model to answer from memory (it can hallucinate), you first *retrieve* relevant passages from your own documents, then give those passages to the LLM as context. The LLM only answers from what you gave it, and every claim maps to a real source. This is what makes the app trustworthy for financial analysis.

**Supabase Row Level Security (RLS)** — Every database table has policies like "users can only read their own rows." These rules are enforced at the database level, not in application code. Even if someone bypassed the API, the database would block the query.

**Server-Sent Events (SSE)** — The chat responses stream word-by-word instead of waiting for the full answer. The backend sends a continuous HTTP response (`text/event-stream`) with JSON chunks, and the frontend renders each chunk as it arrives.

**JWT authentication** — When a user logs in via Supabase, they get a signed JSON Web Token. Every API request includes this token in the `Authorization` header. The backend verifies the token signature with Supabase before processing any request.

**Alembic migrations** — Database schema changes (adding a table, adding a column) are tracked as numbered Python files. You can upgrade or downgrade the schema reliably, and the history is in version control alongside the code.

**Hybrid search + Reciprocal Rank Fusion (RRF)** — Vector (semantic) search and keyword (full-text) search each catch things the other misses: semantic search finds paraphrases and related concepts, keyword search finds exact terms and numbers. Running both and merging their ranked result lists — instead of picking one — catches more relevant passages than either alone. RRF merges the two ranked lists by rank position (`1 / (k + rank)` per list, summed), not by raw score, because cosine similarity and text-search scores live on different, incomparable scales.

**Why keyword extraction matters for full-text search** — Postgres full-text search (`plainto_tsquery`) requires a chunk to contain *every* word in the query. A natural sentence like "How did NVIDIA describe demand drivers for its Data Center business?" has 8+ content words after removing stopwords — almost no single chunk contains all of them, so the raw-query search returns **zero** results in practice (verified against the real corpus). The fix is an LLM step that distills the question down to 3-5 salient search terms (e.g. `"Data Center demand"`) before it ever reaches Postgres.

**Fail-closed validation** — When correctness matters more than always having an answer, every failure mode should refuse rather than guess. The grounding validator here checks citation shape (do the `[1][2][3]` markers in the answer match real citations?) *and* runs a second, independent LLM call asking "does this exact source text actually support this exact claim?" If either check fails, the system retries once, then returns "could not verify" instead of ever showing an unverified answer.

---

## Guides

- [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) — Supabase project setup
- [docs/guides/backend-setup.md](docs/guides/backend-setup.md) — FastAPI + Alembic commands
- [docs/guides/frontend-setup.md](docs/guides/frontend-setup.md) — Vite + React scaffold
- [docs/architecture.md](docs/architecture.md) — System design and data model
- [docs/client-brief.md](docs/client-brief.md) — Driftwood Capital requirements + example questions
