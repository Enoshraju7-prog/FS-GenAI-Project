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
│   │   ├── chat/          # Message conversion + SSE streaming
│   │   ├── database/      # Supabase client, DB query helpers, ORM models
│   │   └── schemas/       # Pydantic request/response models
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

# Install dependencies
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
```

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

---

## Build progress

| Phase | Status | What gets built |
|---|---|---|
| 0 — Prerequisites | ✅ Done | Toolchain, Supabase project, sample SEC corpus |
| 1 — Backend scaffold | ✅ Done | FastAPI app, Supabase schema + migrations, health check |
| 2 — Auth | ✅ Done | Supabase JWT login, protected routes on backend + frontend |
| 3 — Chat shell | ✅ Done | Thread CRUD, streaming stub response, chat UI with sidebar |
| 4 — Ingestion | ⬜ To do | Parse SEC filings → chunks → OpenAI embeddings → Supabase |
| 5 — Retrieval | ⬜ To do | Vector + full-text search, Reciprocal Rank Fusion |
| 6 — LLM agent | ⬜ To do | PydanticAI agent, grounded answers, citation validation |
| 7 — Trust UI | ⬜ To do | Citation chips, source passage panel |
| 8 — Pilot readiness | ⬜ To do | Logging, latency review, end-to-end smoke tests |
| 9 — Deploy (Railway) | ⬜ To do | Production deploy |

---

## Key concepts for interviews

**RAG (Retrieval-Augmented Generation)** — Instead of asking a language model to answer from memory (it can hallucinate), you first *retrieve* relevant passages from your own documents, then give those passages to the LLM as context. The LLM only answers from what you gave it, and every claim maps to a real source. This is what makes the app trustworthy for financial analysis.

**Supabase Row Level Security (RLS)** — Every database table has policies like "users can only read their own rows." These rules are enforced at the database level, not in application code. Even if someone bypassed the API, the database would block the query.

**Server-Sent Events (SSE)** — The chat responses stream word-by-word instead of waiting for the full answer. The backend sends a continuous HTTP response (`text/event-stream`) with JSON chunks, and the frontend renders each chunk as it arrives.

**JWT authentication** — When a user logs in via Supabase, they get a signed JSON Web Token. Every API request includes this token in the `Authorization` header. The backend verifies the token signature with Supabase before processing any request.

**Alembic migrations** — Database schema changes (adding a table, adding a column) are tracked as numbered Python files. You can upgrade or downgrade the schema reliably, and the history is in version control alongside the code.

---

## Guides

- [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) — Supabase project setup
- [docs/guides/backend-setup.md](docs/guides/backend-setup.md) — FastAPI + Alembic commands
- [docs/guides/frontend-setup.md](docs/guides/frontend-setup.md) — Vite + React scaffold
- [docs/architecture.md](docs/architecture.md) — System design and data model
- [docs/client-brief.md](docs/client-brief.md) — Driftwood Capital requirements + example questions
