# RAG Project Playbook

**A start-to-finish guide for building a production RAG application — written from a real build, including every bug we hit and how we fixed it.**

---

## How to use this document

This was written after building **Document Copilot**: a chat app that answers questions about SEC 10-K filings with verifiable citations, deployed to production. Every phase, every configuration value, and every bug below actually happened.

Three ways to use it:

1. **Building something similar?** Follow the phases in order. Each has a checklist and a "bugs we hit here" section — read those *before* you write the code, not after.
2. **Preparing for interviews?** Jump to [Interview talking points](#interview-talking-points). Every claim there is backed by something in this repo.
3. **New to any of these words?** Start with [Core concepts](#core-concepts), which assumes no prior knowledge.

A rule worth internalising before anything else:

> **Verify, don't assume.** Most of the worst bugs in this project were things that *looked* fine. A test suite that ran zero tests. A type-checker checking nothing. Data that rendered wrong because it was *stored* wrong. When something says "OK", ask what it actually checked.

---

## The 30-second version

**The problem.** Financial analysts read hundreds of pages of annual reports before they can do any real analysis.

**The product.** Ask a question in plain English → get an answer where every claim links to the exact passage in the filing it came from.

**The pattern.** RAG — Retrieval-Augmented Generation.

**The stack.**

| Layer | Choice | Why |
|---|---|---|
| Backend | Python + FastAPI | Async, great typing, the AI ecosystem lives in Python |
| Frontend | React + Vite + TypeScript | Plain SPA — no server-side rendering needed |
| UI | Tailwind + shadcn/ui | Components you own as source files, not a dependency |
| Database | Supabase Postgres | Postgres + auth + `pgvector` in one service |
| Vector search | `pgvector` | No separate vector database to run |
| Migrations | SQLAlchemy + Alembic | Versioned, reviewable schema changes |
| Auth | Supabase Auth (email) | JWT + Row Level Security enforced by the database |
| LLM | OpenAI | `gpt-5.5` for answers, `gpt-4.1-mini` for support tasks |
| Hosting | Railway | Two Docker services from one repo |

**Deliberately *not* used:** a separate vector DB (Pinecone/Weaviate), LangChain, a state management library, a frontend test runner. Every one of those was considered and rejected as unnecessary weight for this app.

---

## Core concepts

Read this section if any of the terms below are unfamiliar. Everything after assumes it.

### What is RAG?

An LLM only knows what it was trained on. It has never seen your company's documents, and if you ask about them it will **confidently make things up**.

RAG fixes this with three steps:

1. **Retrieve** — search your documents for passages relevant to the question
2. **Augment** — paste those passages into the prompt
3. **Generate** — ask the model to answer *using only those passages*

The model stops being a knowledge source and becomes a **reasoning engine over evidence you supply**. That single shift is what makes the output trustworthy.

### What is an embedding?

An embedding turns text into a **list of numbers that captures its meaning**.

We use OpenAI's `text-embedding-3-small`, which produces **1,536 numbers** per piece of text. You can picture each text as a point in 1,536-dimensional space. Texts with similar meaning land near each other.

That's the magic: *"How much money did Apple make?"* and *"Apple's total net sales were $391 billion"* share almost no words, but their embeddings sit close together. Keyword search would miss that connection entirely.

### What is a vector database / pgvector?

Something that stores embeddings and answers *"find me the 10 stored vectors closest to this one"* quickly.

You can buy a dedicated one (Pinecone, Weaviate, Qdrant). We used **`pgvector`**, a Postgres extension, because:

- Your documents and your embeddings live in **one database** — no syncing two systems
- You can filter with normal SQL (`WHERE ticker = 'AAPL'`) in the same query as the vector search
- It's one fewer service to run, pay for, and secure

For a corpus of thousands or low millions of chunks, `pgvector` is genuinely enough. Reach for a dedicated vector DB when you outgrow it, not before.

### What is a migration? What is Alembic?

Your database has a **schema** — the tables, columns, and indexes. As you build, the schema changes: new table, new column, new index.

The bad way: click around the database dashboard. Nobody knows what changed, teammates' databases drift apart, and production and local silently differ.

A **migration** is a schema change written as **code, in a file, in version control**. Each has an "up" (apply) and a "down" (undo).

**Alembic** is the tool that manages these for Python/SQLAlchemy. Each migration is a numbered file that knows which migration comes before it, forming a chain:

```
186443db98ec (initial schema)
      ↓
   ff9e028be0d8
      ↓
746bdb2c5339 (add missing RLS write policies)
```

Alembic tracks which migration your database is on. `alembic upgrade head` runs whatever is missing, in order.

```python
def upgrade() -> None:
    op.execute("""
        CREATE POLICY chat_messages_insert_own ON chat_messages
        FOR INSERT TO authenticated
        WITH CHECK (...)
    """)

def downgrade() -> None:
    op.execute("DROP POLICY chat_messages_insert_own ON chat_messages")
```

**Why it matters in interviews:** "we use Alembic so every schema change is reviewable in a pull request and reproducible in every environment" is a real, senior answer.

**Autogenerate is a draft, not an answer.** `alembic revision --autogenerate` compares your models to the database and guesses. It handles tables and columns well. It **does not** understand RLS policies, generated columns, extensions, or specialised indexes — those you write by hand. Always read a generated migration before running it.

### What is Row Level Security (RLS)?

Normally your backend decides who sees what: `SELECT * FROM chats WHERE user_id = <current user>`. Forget that `WHERE` clause once and you've leaked every user's data.

**RLS pushes the rule into the database itself.** You write a policy:

```sql
CREATE POLICY chat_threads_select_own ON chat_threads
FOR SELECT TO authenticated
USING (auth.uid() = user_id);
```

Now Postgres *itself* refuses to return other people's rows, no matter what query the backend sends. A bug in application code can't leak data.

**The critical thing to understand:** RLS is **default-deny per operation**. A `SELECT` policy grants *only* reading. If you never write an `INSERT` policy, **every insert silently fails**. (This bit us — see [Phase 2 bugs](#bugs-we-hit-in-phase-2).)

### What is chunking, and why 512 tokens?

A 10-K filing is hundreds of pages. You can't embed the whole thing — embeddings capture *one* meaning, and a whole annual report doesn't have one meaning. You also can't paste it into a prompt.

So you split documents into **chunks**. Each gets its own embedding and is retrieved independently.

Size is a genuine trade-off:

| Chunk size | Retrieval precision | Context for the model |
|---|---|---|
| Too small (100 tokens) | Sharp — but fragments lose meaning | Not enough to answer |
| **~512 tokens** | **Good balance** | **Enough to stand alone** |
| Too large (2000 tokens) | Blurry — one embedding, many topics | Wastes prompt space |

A **token** is roughly ¾ of a word. 512 tokens ≈ 380 words ≈ a page.

**Chunk on structure, not character count.** Splitting every 512 characters cuts sentences and tables in half. Split on headings and sections first, then subdivide anything still too big.

### What is hybrid search? What is RRF?

Two search methods with opposite weaknesses:

- **Vector search** understands *meaning*, but can miss exact strings. Search `"iPhone"` and it may return passages about "smartphone revenue" while missing the row that literally says iPhone.
- **Full-text (keyword) search** nails exact terms — tickers, product names, numbers — but has no idea `"revenue"` and `"net sales"` mean the same thing.

**Hybrid search runs both and combines them.** But the two return incompatible scores — cosine similarity `0.87` versus a text-rank `0.0031`. You can't average them.

**Reciprocal Rank Fusion (RRF)** solves this by throwing away the scores and using only the **ranks**:

```
score(document) = Σ  1 / (k + rank_in_that_list)
```

with `k = 60` by convention. A document ranked #1 in vector search and #3 in keyword search scores `1/61 + 1/63`. Appearing high in *both* lists beats appearing first in only one.

**Why it's elegant:** it needs no tuning, no score normalisation, and no knowledge of how either engine scores. It just asks "did both methods agree this was good?"

### What is grounding, and what does "fail-closed" mean?

The model could still write a beautiful answer with a fabricated citation. So after generation we **validate**:

1. Every `[1]`, `[2]` marker must map to a real retrieved chunk
2. A separate model call checks the claim is actually supported by that chunk
3. Citations the answer never referenced are pruned

**Fail-closed** means: if validation fails, we **do not show the answer**. We retry once with stricter instructions, then refuse.

This is the opposite of most demos, which show whatever the model said. For a financial tool the calculus is obvious: a wrong answer that *looks* sourced is far worse than no answer.

### What is streaming (SSE)?

These queries take 60–90 seconds. A blank screen for 90 seconds looks broken.

**Server-Sent Events** is a one-way stream from server to browser over a normal HTTP connection. The server pushes events as they happen; the browser renders them live. Simpler than WebSockets, and one-way is all we need.

We stream three kinds of event: **status** ("Searching SEC filings…"), **text** (the answer, word by word), and **citations**.

### What is a JWT?

A **JSON Web Token** — a signed string proving who you are. Supabase issues one at login. The browser sends it on every request as `Authorization: Bearer <token>`. The backend verifies the signature, so it knows the user without a database lookup, and RLS reads the user id straight out of it.

---

## Phase 0 — Prerequisites

**Goal: everything installed and connected before you write a line of app code.**

### Checklist

- [ ] Language toolchains — Python 3.12+, Node LTS
- [ ] Package managers — `uv` (Python), `pnpm` (Node). Pick one each and **commit to it**; mixing `npm` and `pnpm` corrupts lockfiles.
- [ ] Supabase project created; save the URL, anon key, service-role key, and database URL
- [ ] OpenAI API key **with a spending limit set** (see [Cost](#cost-management) — do this on day one)
- [ ] Git repo initialised, `.gitignore` covering `.env`, `.venv`, `node_modules`, `dist`
- [ ] Corpus downloaded to a **gitignored** folder — never commit source documents
- [ ] Docker Desktop installed (you'll need it at deploy time; installing it early avoids a scramble)

### Decide these now, write them down

Write an `AGENTS.md` / `CLAUDE.md` at the repo root stating your stack and rules. It keeps *you* honest as much as any AI assistant:

- **Dependency policy.** Ours: *write it yourself unless the alternative is non-trivial, error-prone, or reinventing a standard.* An HTTP client, a Markdown parser, an ORM — fine. A library wrapping 20 lines of stdlib — no.
- **One settings module per service.** Never call `os.getenv` scattered through the code.
- **Fail fast on startup** if required config is missing. A missing key should crash at boot with a clear message, not produce a confusing 500 an hour later.

### A supply-chain guard worth copying

```
# frontend/.npmrc
minimum-release-age=10080   # 7 days, in minutes
```

This refuses any package version published less than 7 days ago. It defends against the typosquat / compromised-release window, where a malicious version of a popular package goes live and gets pulled within hours. `uv` has an equivalent: `exclude-newer = "7 days"`.

---

## Phase 1 — Backend scaffold + database schema

**Goal: a FastAPI app that starts, answers `/health`, and owns its schema through migrations.**

### Checklist

- [ ] FastAPI app with a `/health` endpoint returning `{"status": "ok"}`
- [ ] Single settings module (`app/config.py`) using pydantic-settings
- [ ] SQLAlchemy models for every table
- [ ] Alembic initialised, pointed at your models
- [ ] Initial migration written **and read line by line** before applying
- [ ] RLS enabled with policies for **every operation you use**
- [ ] Connection pool configured explicitly

### Build `/health` first

It feels trivial. It is the endpoint your deployment platform polls to decide whether your app is alive, and it's the first thing you curl when something breaks. Build it in the first five minutes.

### Schema shape for a RAG app

```
users               -- mirrors auth users
source_documents    -- one row per source file (filing, PDF, page)
document_chunks     -- the searchable pieces + embeddings
document_tables     -- extracted tables, stored once, normalised
chat_threads        -- conversations
chat_messages       -- messages within a thread
message_citations   -- links an answer to the chunks that support it
```

The `document_chunks` table is the heart:

```python
class DocumentChunk(Base):
    id: Mapped[uuid.UUID]
    document_id: Mapped[uuid.UUID]       # FK to source_documents
    table_id: Mapped[uuid.UUID | None]   # FK to document_tables, if this is a table
    chunk_index: Mapped[int]             # order within the document
    text: Mapped[str]                    # what gets embedded and shown
    embedding: Mapped[Vector]            # pgvector column, 1536 dims
    token_count: Mapped[int]
    chunk_metadata: Mapped[dict]         # JSONB
```

**`chunk_index` is doing more work than it looks.** It's what lets you fetch "the chunk before and after this one" — which is how the source panel shows a citation in context instead of as a floating fragment.

### Things Alembic autogenerate will NOT write for you

Write these by hand in the migration:

```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
op.execute("CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)")
op.execute("CREATE INDEX ... USING gin (text_search)")
op.execute("CREATE POLICY ...")
```

### Configure the connection pool explicitly

```python
_engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_size=settings.db_pool_size,        # 10
    max_overflow=settings.db_max_overflow,  # 20
    pool_pre_ping=True,
    pool_recycle=1800,
)
```

**`pool_pre_ping=True` is the highest-value line here.** Hosted Postgres closes idle connections. Without a pre-ping, the first query on a stale connection fails with an error that looks completely random and is miserable to debug.

**Default pool size is 5 + 10 overflow = 15.** That is too small for anything with concurrent users, because every request that runs blocking SQL holds a connection for its whole duration. We found this by reading the code during a readiness review — before it caused an outage.

### Bugs we hit in Phase 1

**Connection string: session vs transaction pooler.** Supabase offers three ways in, and choosing wrong breaks things subtly:

| Connection | Host | Port | Mode | Works with Alembic? |
|---|---|---|---|---|
| Direct | `db.<ref>.supabase.co` | 5432 | Session | ✅ but **IPv6 only** |
| **Session pooler** | `<region>.pooler.supabase.com` | **5432** | Session | ✅ **and IPv4** |
| Transaction pooler | `<region>.pooler.supabase.com` | 6543 | Transaction | ❌ no prepared statements |

Advice everywhere says "don't use the pooler." What it *means* is "don't use the **transaction** pooler on 6543." Port **5432** on the pooler host is session mode — fully compatible, and IPv4, which many hosting platforms need since the direct host is IPv6-only. **Read the port, not just the hostname.**

---

## Phase 2 — Authentication

**Goal: users log in, and can only ever see their own data.**

### Checklist

- [ ] Supabase Auth configured (email/password)
- [ ] Backend dependency that verifies the JWT and returns the current user
- [ ] Frontend route guard redirecting unauthenticated users to `/login`
- [ ] **Per-request** Supabase client using the user's token (not a shared admin client)
- [ ] RLS policies for **SELECT, INSERT, UPDATE, and DELETE** — all four
- [ ] Auth redirect URLs configured for **every** environment you deploy to

### Two clients, two purposes

```python
async def create_user_client(access_token: str) -> AsyncClient:
    """Fresh per-request client using the anon key + user JWT.

    RLS policies evaluate auth.uid() from the Bearer token, so the user
    only sees rows they own.
    """
```

- **User client** — anon key + the user's JWT. RLS applies. Use this for essentially everything.
- **Service-role client** — bypasses RLS entirely. Use *only* where you deliberately need to look past a user's own rows, and check ownership yourself immediately.

We use the service-role client in exactly one place: distinguishing "thread doesn't exist" (404) from "thread belongs to someone else" (403). RLS alone would make both look like 404.

### Bugs we hit in Phase 2

**🐛 RLS default-deny broke persistence — and looked like a frontend bug.**

Symptom: chat worked perfectly, answers streamed... and then vanished on reload. Threads stayed titled "New chat" forever.

The initial migration created:

```sql
CREATE POLICY chat_messages_select_own    ON chat_messages   FOR SELECT ...
CREATE POLICY chat_threads_select_own     ON chat_threads    FOR SELECT ...
CREATE POLICY chat_threads_insert_own     ON chat_threads    FOR INSERT ...
```

Spot what's missing: **no INSERT policy on `chat_messages`**, no UPDATE, no DELETE on `chat_threads`.

RLS is **default-deny per operation**. Reading worked. Every write silently failed. And because the write happened after the response streamed, the user saw a perfect answer that was never saved.

The backend traceback said it plainly, once we looked:

```
postgrest.exceptions.APIError: new row violates row-level security policy
for table "chat_messages"
```

**Fix:** a migration adding the missing policies.

**Lessons:**
1. When you enable RLS, **enumerate all four operations** for every table, every time.
2. Symptoms far from the cause are the norm. "Data disappears on reload" sounds like frontend state; it was a database policy.
3. **Read the server logs.** The answer was sitting in them the whole time.

---

## Phase 3 — Chat shell

**Goal: create threads, send messages, stream a response — before any AI is involved.**

Build the plumbing with a stub that streams "Hello, world" one word at a time. Getting streaming right is fiddly; do it while the thing you're streaming is trivial to reason about.

### Checklist

- [ ] Thread CRUD endpoints
- [ ] SSE streaming endpoint with a stubbed response
- [ ] Frontend chat UI: message list, input, streaming render
- [ ] Message persistence
- [ ] Error states — network failure, auth failure, server error

### The message-part model

Define your wire format early. Ours mirrors the Vercel AI SDK:

```python
class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str

class CitationPart(BaseModel):
    type: Literal["data-citation"] = "data-citation"
    data: CitationPayload

class StatusPart(BaseModel):
    type: Literal["data-status"] = "data-status"
    data: StatusPayload

MessagePart = Annotated[TextPart | CitationPart | StatusPart, Field(discriminator="type")]
```

A message is a **list of parts**, not a string. That's what lets one assistant message contain prose, citations, and progress updates together.

`discriminator="type"` tells Pydantic to read `type` and jump straight to the right model — faster, and it produces a precise error instead of a vague one.

### Bugs we hit in Phase 3

**🐛 The chat client library replayed status parts, causing a 422 on the *third* message.**

The AI SDK keeps every part — including transient status updates — on the assistant message in memory. On the next question it replays the whole history to the server. Our schema only accepted `text` and `data-citation`:

```
Input tag 'data-status' found using 'type' does not match any of the
expected tags: 'text', 'data-citation'
```

First message fine. Second fine. **Third one failed** — which is exactly why it was baffling.

**Fix, at both ends:**
- Backend accepts `StatusPart` in the union (any compliant client will send them)
- Frontend strips them before sending, or the payload grows by an entire progress trail every turn

**Lesson:** when a bug appears on the *Nth* interaction but not the first, suspect **accumulated state**.

**🐛 Wrong option name silently posted to the wrong URL.** We wrote `new DefaultChatTransport({ url: ... })`. The real option is `api`. With `url`, the SDK fell back to its default `/api/chat` and every message 404'd against the *frontend* dev server. Found only by opening the browser's network tab.

**Lesson:** a config object with an unknown key usually **doesn't error** — it ignores you and uses a default. When something targets the wrong place, check the option names against the installed version.

---

## Phase 4 — Ingestion: parse → chunk → embed → store

**This is where RAG quality is actually decided.** Retrieval and prompting can't recover from bad chunks.

### Checklist

- [ ] Parse source documents to structured text
- [ ] **Handle tables deliberately** — do not leave them to a generic converter
- [ ] Chunk on structure, then by token budget
- [ ] Attach metadata to every chunk (source, date, section, page)
- [ ] Embed in batches
- [ ] Store with **batched** database writes
- [ ] Verify: re-read stored chunks and check they're readable

### The pipeline, concretely

```
filing.htm
   ↓  Docling (document structure) + custom table extractor
   ↓  chunk on headings, split anything > 512 tokens
   ↓  OpenAI text-embedding-3-small → 1536 numbers per chunk
   ↓  batched INSERT into document_chunks
```

### Tables will be your hardest problem

If your documents contain tables — financial filings, reports, spec sheets — **budget real time for this**. Two structural problems:

**1. Markdown cannot express merged cells.** HTML has `colspan="3"`. Markdown tables require every row to have the same number of `|` cells. There is no syntax for a cell spanning columns. So converters **repeat the text once per column**:

```html
<td colspan="3">iPhone</td>
```
becomes
```
| iPhone | iPhone | iPhone |
```

**2. Layout tables.** SEC filings open every table with ~30 invisible spacer cells that only control column widths. A generic converter counts them as real columns, producing an empty header row.

**The fix: own your table extraction.** We wrote a parser that reads the source HTML directly, understands `colspan`, discards spacer cells, and captures title, units, and footnotes. It produced perfect output while the generic converter produced garbage.

### Bugs we hit in Phase 4

**🐛 The two-parser handoff — 109 of 152 table chunks were silently corrupted.**

We ran **two** parsers over the same file: a document parser for structure, and our own table extractor. Then we matched them up by searching each document chunk for the table's first row label.

The document parser splits a long table across **many** chunks:

```
piece 1:  header + iPhone + Mac       ← contains "iPhone"  → matched ✅
piece 2:  iPad + Wearables            ← no "iPhone"        → FELL THROUGH ❌
piece 3:  Services + Total            ← no "iPhone"        → FELL THROUGH ❌
```

Unmatched pieces hit a fallback that wrote the *generic converter's mangled markdown* straight into the database. **109 of 152 table chunks — 48% of all narrative content — was corrupt.**

**Fix: make the boundary absolute.**

> The document parser owns prose. The table extractor owns every table. A generically-serialized table must **never** reach the database.

We deleted the fallback entirely. Result: **109 → 0**.

**Lessons:**
1. When two systems produce overlapping output, define **one owner per data type** and enforce it. Fuzzy reconciliation fails silently.
2. **A fallback that produces bad data is worse than an error.** If we'd raised an exception, we'd have found it in an hour instead of weeks.
3. **Read your stored data.** Query the database and actually look at what's in there.

**🐛 Silent drops: three real tables per filing vanished.**

Our extractor assumed the first text row was always a header. Maturity schedules have **no header** — the first row is already data:

```
2026    $ 12,393
2027      10,078
Total   $ 91,285
```

It treated `2026 | $ | 12,393` as column names, invented columns nothing could fill, returned `None`, and discarded the table **in silence**.

**Fix:** a shape detector for schedules, plus a loud warning when anything is dropped:

```python
if normalized is None:
    print(f"WARNING: could not normalize table {title!r} — dropped", file=sys.stderr)
```

**And a test for the opposite direction.** Our first attempt used "does this look like money?", which was too greedy — it would have swallowed genuine multi-column rows like `Net sales | $ | 391,035 | $ | 383,285`, breaking tables that already worked. The final rule is "label plus **exactly one** amount", locked in by a test.

**Lesson:** when you widen a parser, write a test proving it still **rejects** what it should. A fix that quietly breaks working cases is worse than the original bug.

**🐛 Statement timeout on large documents.**

The full re-ingest died after 5 of 25 files:

```
psycopg.errors.QueryCanceled: canceling statement due to statement timeout
```

580 chunks wrote fine; 767 didn't. Everything was going in **one statement**, each row carrying a 1,536-number vector.

```python
INSERT_BATCH_SIZE = 200

for offset, (record, embedding) in enumerate(zip(records, vectors, strict=True)):
    session.add(DocumentChunk(...))
    if (offset + 1) % INSERT_BATCH_SIZE == 0:
        session.flush()

session.commit()
```

**`flush()` sends queued SQL but stays in the transaction. `commit()` ends it.** So batched flushes keep each statement small while the single commit keeps the whole file **atomic**.

`strict=True` on `zip` raises if the lists differ in length instead of silently truncating — which would pair chunks with the *wrong embeddings* and corrupt search invisibly.

**🐛 The storage explosion — 500 MB, 106% of quota.**

Two compounding design mistakes:

1. **One chunk per table *row*.** A 6-row table became 6 chunks and 6 embeddings.
2. **Every row-chunk stored a full JSON copy of its entire parent table.** The iPhone row carried all 6 rows. So did Mac. So did iPad.

Across the corpus: 12,011 row-chunks carrying **40 MB of pure duplication** — data already stored once, properly, in a 6 MB `document_tables` table that `document_chunks.table_id` already pointed at.

**Fix:** one chunk per **table**, split by row groups only when over the token budget, with the table blob stored **once** on the first chunk.

| | before | after |
|---|---|---|
| chunks | 19,544 | **6,051** |
| database | 511 MB | **142 MB** |

**Nothing was lost** — the whole-table chunk contains every row, and `document_tables` still holds every table. We removed *copies*, not originals. There was even an accuracy **gain**: "how did the mix shift?" needs the whole grid at once, which row-level chunks could never retrieve.

**Lessons:**
1. **Metadata is not free.** A dictionary attached to 12,000 rows is a design decision.
2. **If it's already in another table with a foreign key, don't copy it.** That's what the FK is for.
3. Watch chunk **count**, not just corpus size. Chunk count drives storage, index size, and embedding cost.

---

## Phase 5 — Retrieval: hybrid search + RRF

**Goal: given a question, return the passages most likely to contain the answer.**

### Checklist

- [ ] Vector similarity search over `pgvector`
- [ ] Postgres full-text search
- [ ] RRF fusion of both result sets
- [ ] Metadata filters (company, year, document type)
- [ ] Neighbour lookup for context

### The flow

```
question
   ↓
   ├─→ embed → vector search  → top 50 candidates
   └─→ extract keywords → full-text search → top 50 candidates
                    ↓
              RRF fusion (k=60)
                    ↓
              top 5 passages
```

### Tuning values, and what each means

| Setting | Value | What it controls |
|---|---|---|
| `retrieval_candidate_k` | 50 | Candidates from *each* engine before fusion. Costs no tokens — it's all database side. |
| `retrieval_top_k` | **5** | Passages sent to the model. **Directly multiplies token cost.** |
| `retrieval_rrf_k` | 60 | RRF smoothing constant. The conventional value; leave it. |
| `retrieval_neighbor_radius` | 1 | Chunks either side fetched for context. |

**Fetch wide, send narrow.** Fusion is better with 50 candidates per engine, and it's free. What you *send to the model* is the expensive part.

### Extract keywords before full-text search

Feeding a whole question into Postgres full-text search works badly — every filler word becomes a search term. We use a **cheap model** (`gpt-4.1-mini`) to pull 3–5 meaningful keywords first, with a deterministic fallback and a fast path for short queries.

**Why a small model here:** this is a mechanical task with a tiny output. Using an expensive model would be waste. **Match the model to the job.**

### Bugs we hit in Phase 5

**🐛 Search ran before keywords were extracted.** An ordering bug — the full-text query fired with the raw question. Fixed by extracting first, then searching, and parallelising the two engines with `asyncio.gather`.

**Lesson:** in async code, **order is something you have to state**. Two operations that look sequential in the source may not be.

---

## Phase 6 — The LLM agent and grounding

**Goal: turn passages into an answer where every claim is verifiable.**

### Checklist

- [ ] Agent with retrieval tools (search, read chunk, read surrounding)
- [ ] Structured output — answer text plus citation list
- [ ] Citation validation against actually-retrieved chunks
- [ ] Fail-closed on validation failure
- [ ] A registry of what was retrieved this turn
- [ ] Request limit to bound cost and latency

### Model choices, and why each

| Job | Model | Reasoning |
|---|---|---|
| **Writing the answer** | `gpt-5.5` | The hard task: read financial passages, reason across years, cite precisely. Quality here *is* the product. |
| **Validating citations** | `gpt-4.1-mini` | Narrow yes/no: "does this passage support this claim?" A small model is reliable and ~20× cheaper. |
| **Extracting keywords** | `gpt-4.1-mini` | Mechanical, tiny output. |
| **Embeddings** | `text-embedding-3-small` (1536 dims) | Strong quality per dollar. `-large` costs more and, for this corpus, didn't earn it. |

**The principle: use the expensive model where judgment matters, cheap models everywhere else.** When we needed to cut costs, we deliberately kept `gpt-5.5` for answers — a smoke test had proven it grounded 10/10 — and cut *token volume* instead. Never downgrade the model doing the thing your product is *for*, until you've exhausted the cheaper levers.

### The agent loop, and why it's expensive

```
1. Model reads the question
2. Calls search_filings(...)      → passages come back
3. Maybe calls read_chunk(...)    → more text
4. Maybe searches again
5. Writes the answer with citations
```

**The critical cost fact:** each iteration re-sends the **entire conversation so far**, including every passage retrieved. Ten iterations doesn't cost 10× the first — it costs far more, because the context grows each time.

That's why `openai_agent_request_limit` matters. We cut it 20 → 8.

### Validation

```python
for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
    grounded = await run_agent(query, deps)
    grounded = prune_unreferenced_citations(grounded)
    validation = await GroundingValidator().validate(grounded, registry)
    if validation.ok or attempt == MAX_VALIDATION_ATTEMPTS:
        break
    # retry with stricter grounding instructions
```

Note the **cost implication**: a failed validation re-runs the *whole agent*. Worth it — grounding is the product — but it means the retry limit and the request limit multiply.

---

## Phase 7 — Trust UI

**Goal: make verification effortless. This is where a RAG demo becomes a RAG product.**

### Checklist

- [ ] Inline citation chips that are clickable
- [ ] Source panel showing the exact passage **plus neighbouring context**
- [ ] Markdown rendering (tables matter enormously)
- [ ] Live status while waiting
- [ ] Empty, loading, and error states for every surface
- [ ] Keyboard accessible, screen-reader friendly

### Show neighbours, not just the citation

A single chunk read alone feels like it came from nowhere. Show **previous / cited / next**:

```
┌─ PREVIOUS CONTEXT ─ Chunk 62 ─┐
│ ...leading into the table      │
├─ CITED PASSAGE ─── Chunk 63 ──┤   ← visually distinct
│ | Category | 2025 | 2024 |     │
├─ NEXT CONTEXT ──── Chunk 64 ──┤
│ ...notes that follow           │
└────────────────────────────────┘
```

This is a small endpoint (`GET /chunks/{id}/context`) and a large trust improvement.

### Status: replace, don't accumulate

We tried three designs:

1. Current step + a collapsed list of finished steps
2. A full breadcrumb: `Analyzing › Searching › Reading › Verifying › Answering`
3. ✅ **One line that swaps as the run advances, with a gradient shimmer**

The third won. The motion carries "still working", so no spinner is needed, and there's no visual clutter.

```jsx
<p role="status" aria-live="polite" className="text-shimmer text-sm">
  {status?.message ?? "Thinking…"}
</p>
```

`aria-live="polite"` makes screen readers announce changes without interrupting. And respect `prefers-reduced-motion` — some people get motion sickness from animation; the OS setting exists for a reason.

### Bugs we hit in Phase 7

**🐛 Markdown tables rendered as a wall of pipes.** GitHub-Flavored Markdown only recognises a table if its header **begins a new block**. Models and documents routinely write:

```
Units: dollars in millions
| Category | 2025 | 2024 |
```

With no blank line, the parser treats every row as continuation of that paragraph. Fixed by inserting the blank line the parser expects.

**Crucially — this fix could not have saved the corrupted tables from Phase 4.** Those were wrong *in the database*. **Know which layer a bug lives in.** A rendering fix only helps data that was already correct.

**🐛 Citations opened a blank browser tab.** In Markdown, `[1](something)` is **link syntax**. Whenever a citation marker was followed by a parenthesis, it parsed as a link and rendered `<a target="_blank">`. Fixed by treating any anchor whose label is just a citation number as a chip.

**🐛 A blank page from a component-library context error.** Clicking the user menu blanked the entire app. The real error, once we actually looked:

```
Base UI: MenuGroupContext is missing. Menu group parts must be used
within <Menu.Group> or <Menu.RadioGroup>.   at MenuGroupLabel
```

A label component required a group parent it didn't have. It threw, React unmounted the tree, blank page.

**Two lessons, and the second one is the important one:**
1. Composite component libraries often require specific parent/child structure. The error message told us exactly what was wrong.
2. **The first fix was wrong.** We'd guessed at a different cause and patched it. The user reported it still broken — and mentioned it also happened when merely *opening* the menu, which doesn't sign out at all. That detail disproved the theory. **When a user says it's still broken, believe them and go reproduce it.** Guessing twice is how you burn an afternoon.

**🐛 The page wouldn't scroll.** Two CSS causes, both about height:

- `items-center` on a flex container **overrides `align-items: stretch`**, so the child stops filling the height. Tall content then overflows in *both* directions and can't scroll.
- `min-h-svh` is a **minimum**, letting the page grow instead of the inner list scrolling. An internal scroller needs a **definite** height above it.

```jsx
<SidebarProvider className="h-svh overflow-hidden">
  <SidebarInset className="min-h-0 overflow-hidden">
```

**`min-h-0` is the classic flexbox gotcha.** Flex items default to `min-height: auto` and refuse to shrink below content size, so a scrollable child never gets constrained.

**🐛 Invisible logo in dark mode.** A black-on-transparent logo disappears on a dark background. `dark:invert`. Also check your component library's dark palette for stray colours — shadcn's default dark theme ships a blue-violet `--sidebar-primary` that looked wrong in an otherwise monochrome design.

---

## Phase 8 — Pilot readiness

**Goal: know it works, know what it costs, know what happens when it breaks.**

### Checklist

- [ ] Structured logging with request identifiers
- [ ] **Tracebacks captured on failure** — not just error strings
- [ ] Smoke test over real questions from the actual brief
- [ ] Latency measured and written down
- [ ] Connection pool sized for expected concurrency
- [ ] No single-user shortcuts in the request path
- [ ] Setup instructions complete enough for a stranger

### Structured logging

```python
turn_log = log.bind(thread_id=str(thread_id), user_id=str(user.id))
turn_log.info("turn_started", query_chars=len(query))
...
turn_log.exception("agent_run_failed", attempt=attempt, error=str(exc))
...
turn_log.info("turn_completed", grounded=validation.ok,
              citations=len(grounded.citations), elapsed_s=round(elapsed, 2))
```

Three things worth copying:

1. **`.bind()`** attaches identifiers once; every later line carries them, which is what makes logs searchable.
2. **Event name first, then key=value.** `turn_completed` with an `elapsed_s` field lets you ask "what's the median?" later. A sentence buried in a string doesn't.
3. **`.exception()` captures the traceback.** Our orchestrator caught every agent error and put only `str(exc)` on the wire — **throwing the traceback away**, making failures undebuggable. This is a very common mistake.

Console renderer locally, JSON when deployed — same code, controlled by config.

### Actually run the smoke test

Take the real example questions from your brief and run every one end to end. Ours: **10/10 grounded**, 3–15 citations each.

Also record latency honestly. Ours: **99s to 409s**, median ~175s. That is *slow*. Status text appears immediately so it never looks frozen, but it's a real limitation worth stating plainly rather than hiding.

### Bugs we hit in Phase 8

**🐛 The type-checker was checking nothing.**

We ran `pnpm tsc --noEmit` all session and it passed. It was checking **zero files**.

The root `tsconfig.json` was a *project references* file — `"files": []` plus a `references` array. Running `tsc` against it checks the empty file list and exits happily.

The real check was `pnpm build` (`tsc -b && vite build`). Switching to it **immediately surfaced three real errors** that had been hiding for hours.

**Lesson — and this is the one to remember from the whole document:** *a green check mark means nothing until you've confirmed the check actually ran.* Break something on purpose and make sure your tooling notices.

**🐛 Related: a CLI writing files to the wrong place.** The component CLI kept creating a literal `@/` directory instead of resolving the alias, because it reads the *root* tsconfig directly rather than following project references. Fixed by adding `paths` to the root config too. **Tooling that reads config files may not resolve them the way the compiler does.**

---

## Phase 9 — Deployment

**Goal: live, reachable, and reproducible.**

### Checklist

- [ ] Dockerfile per service
- [ ] `.dockerignore` excluding `.env`, `node_modules`, `.venv`, build output
- [ ] Health endpoint per service
- [ ] Images **built and run locally** before deploying
- [ ] Environment variables set on the platform
- [ ] Domains generated
- [ ] CORS configured
- [ ] Auth redirect URLs updated for production
- [ ] Verified in a real browser

### Monorepo: one service per app

If your repo looks like this:

```
├── backend/     (pyproject.toml here)
├── frontend/    (package.json here)
└── README.md
```

...then a build platform pointed at the **root** finds nothing it recognises and fails in seconds. That's exactly what happened to us:

```
railpack process exited with an error
```

**Fix:** one service per app, each told which subdirectory it owns (`railway up ./backend --path-as-root`, or a Root Directory setting).

### Why Dockerfiles over auto-detection

Auto-detection is convenient until it guesses wrong. Dockerfiles are explicit, testable locally, and identical in every environment. **Building the image on your laptop first turns a 10-minute remote debug cycle into a 30-second local one.**

### Backend Dockerfile — the parts that matter

```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project    # ← cached layer

COPY app ./app
RUN uv sync --frozen --no-dev

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Five details, each of which breaks something if wrong:

1. **`PYTHONUNBUFFERED=1`** — Python buffers stdout when not attached to a terminal. Without this your logs appear minutes late or never. The most common "why are there no logs?" cause.
2. **Dependencies copied before source** — Docker caches layers, so editing your code doesn't reinstall 240 packages.
3. **`--frozen`** — install exactly what the lockfile says. Reproducible builds.
4. **`--host 0.0.0.0`** — `127.0.0.1` means "only from inside this container." The platform's proxy is outside. Symptom: a confusing healthcheck timeout.
5. **`exec`** — makes your server PID 1 so it receives shutdown signals directly. Without it the shell swallows `SIGTERM` and the container gets killed hard.

### Frontend: build-time vs runtime variables

**The concept people most often get wrong.**

A React SPA is static files running in a browser. There is no server-side environment to read. So Vite **inlines** `VITE_*` values into the JavaScript **at build time**, literally substituting the text.

Setting `VITE_API_BASE_URL` as a *runtime* variable does **nothing** — the bundle was already written.

```dockerfile
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build          # ← must come after
```

**Verify it worked** rather than hoping:

```bash
curl -s $FRONTEND/assets/index-*.js | grep -c "your-backend-domain"
# 1 = baked in.  0 = you're about to debug a mystery.
```

### Two-stage build

```dockerfile
FROM node:lts-alpine AS build
RUN pnpm build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
```

Stage two discards Node, pnpm, `node_modules`, and all source. **86 MB instead of ~1 GB.**

### SPA routing: order your routes

A React Router app needs the server to return `index.html` for *any* path — visit `/chats/abc-123` directly and no such file exists, but the browser must still get the app.

```
:{$PORT:3000} {
	@health path /health
	handle @health { respond "ok" 200 }     # ← specific route FIRST

	handle {
		root * /srv
		try_files {path} /index.html         # ← catch-all LAST
		file_server
	}
}
```

**If the catch-all came first, `/health` would return your homepage** — a 200 that tells you nothing. Specific before catch-all, always.

### Deploy order (a genuine chicken-and-egg)

```
1. Deploy backend
2. Generate backend domain
3. Set frontend's VITE_API_BASE_URL = backend domain   ← build-time!
4. Deploy frontend
5. Generate frontend domain
6. Set backend's ALLOWED_ORIGINS = frontend domain     ← CORS
7. Redeploy backend
8. Update auth redirect URLs
```

**CORS** = browsers block a page on origin A from calling API B unless B explicitly permits A. Verify with a real preflight:

```bash
curl -X OPTIONS "$BACKEND/api/endpoint" -H "Origin: $FRONTEND" \
     -H "Access-Control-Request-Method: GET" -D-
# look for: access-control-allow-origin: <your frontend>
```

### Keep heavy optional dependencies out of the runtime image

Our document parser pulls PyTorch and CUDA — gigabytes — and is used **only** by the offline ingestion script, never by the API.

```toml
[project.optional-dependencies]
ingest = ["docling==2.115.0"]
```

**Verify before moving anything:**

```bash
grep -rn "^from ingest\|import docling" app/    # no output = safe
```

Result: **807 MB instead of multiple GB.** Ingestion runs locally with `uv sync --extra ingest`.

### Bugs we hit in Phase 9

**🐛 CORS returned 400 — and it was a false alarm.** Setting `ALLOWED_ORIGINS` *triggers a redeploy*. We tested while the backend was restarting. Retesting after it settled gave a clean 200.

**Lesson:** when something fails moments after a deploy, **check the thing is actually up** before changing code. We nearly "fixed" a working configuration.

**🐛 Auth redirect URLs — and an overstatement worth correcting.** We initially said sign-in would fail without configuring the production URL. That was wrong, and the accurate version is more useful:

| Flow | Blocked without config? |
|---|---|
| Existing user, email + password | **No** — a direct API call, not origin-gated |
| New user sign-up confirmation email | **Yes** — the link points at `localhost` |
| Password reset email | **Yes** — same |

**Lesson:** be precise about *what* breaks. "Everything is broken" and "new user onboarding is broken" lead to very different priorities.

---

## Cost management

### What we actually spent

**$7.52 in one day — 2.65M input tokens across 339 requests.** That's ~7,800 input tokens *per request*.

### Where it goes

The agent loop is the multiplier. Each iteration re-sends the whole conversation including every retrieved passage:

```
cost ≈ (passages × passage_size) × iterations × price_per_token
```

Our original settings multiplied out badly: 10 passages × (800 chars + 2 neighbours × 800) ≈ 6,000 tokens per search, × up to 20 iterations.

### The levers, in order of impact

| Lever | Before | After | Effect |
|---|---|---|---|
| Neighbours inlined in search results | yes | **no** | Removed ~⅔ of each search payload |
| `retrieval_top_k` | 10 | **5** | Halved passages |
| Agent request limit | 20 | **8** | Capped the multiplier |
| Excerpt chars | 800 | **500** | Smaller passages |

Roughly **60–70% fewer input tokens per turn — with no model change.**

### Rules of thumb

1. **Set a hard spend cap on day one.** Code limits reduce cost; a budget cap *bounds* it. Only one of those saves you from a runaway loop.
2. **Cut volume before you cut quality.** Downgrading the model that writes your answers is the *last* lever, not the first.
3. **Small models for mechanical tasks.** Keyword extraction and yes/no validation don't need a frontier model.
4. **Watch the multiplier, not the single call.** One request looks cheap. Twenty iterations of a growing context is where the money goes.
5. **Be careful with full smoke tests.** Ours — 10 complex questions end to end — was a large share of one day's spend. Worth running, but deliberately.

---

## Interview talking points

Each of these maps to something real in this repo.

**"Walk me through your RAG pipeline."**
> Documents are parsed with a custom extractor for tables and a general parser for prose, chunked on structure at ~512 tokens, embedded with `text-embedding-3-small`, and stored in Postgres with `pgvector`. A query runs vector *and* full-text search in parallel, fuses them with Reciprocal Rank Fusion, and hands the top passages to an agent that must cite them. Every citation is validated before the answer is shown — if validation fails we refuse rather than guess.

**"Why not a dedicated vector database?"**
> `pgvector` keeps documents and embeddings in one database, so metadata filters and vector search happen in a single SQL query with no syncing between systems. For thousands to low millions of chunks that's plenty. I'd move to a dedicated store when scale or query patterns demanded it — not by default.

**"Why hybrid search?"**
> Vector search understands meaning but misses exact strings like tickers. Keyword search nails exact terms but doesn't know "revenue" and "net sales" are the same. RRF combines them using only ranks, so it needs no score normalisation and no tuning — it just rewards documents both methods agreed on.

**"How do you stop hallucination?"**
> Three layers. The agent can only cite chunks it actually retrieved, tracked in a per-turn registry. A validator model checks each claim against its cited passage. And it's fail-closed — if validation fails we retry once with stricter instructions, then refuse. A wrong answer that looks sourced is worse than no answer.

**"Tell me about a hard bug."**
> Citations were displaying garbled tables. It looked like a rendering bug, but the corrupted text was in the database. We ran two parsers over the same documents and reconciled them by fuzzy text matching. Large tables get split across many chunks, so only the first fragment matched — 109 of 152 table chunks fell through to a fallback that stored the bad output. The fix was to make the boundary absolute: one parser owns prose, the other owns tables, and delete the fallback. 109 to 0. The lesson was that a fallback producing bad data is worse than an error.

**"How do you control LLM costs?"**
> The dominant term is the agent loop, because each iteration re-sends the whole context. I cut passages per search, excerpt size, inlined neighbours, and the iteration cap — about 60–70% fewer tokens without changing the model. I keep the frontier model where judgment matters and cheap models for mechanical tasks like keyword extraction. And a hard budget cap, because code limits reduce cost but only a cap bounds it.

**"What would you do differently?"**
> Verify tooling earlier. I ran a type-checker for hours that was checking zero files because of how project references work. And I'd read stored data sooner — the table corruption was visible in the database the whole time; I was debugging the display layer.

---

## Pre-flight checklist for the next project

Print this. Work down it.

### Before writing code
- [ ] Stack decided and written into `AGENTS.md` / `CLAUDE.md`
- [ ] Dependency policy stated
- [ ] **OpenAI spending limit set**
- [ ] `.gitignore` covers `.env`, `.venv`, `node_modules`, `dist`, corpus data
- [ ] Package-manager release-age guard configured

### Database
- [ ] Migrations from commit one — never click the dashboard
- [ ] RLS enabled with **all four operations** policied per table
- [ ] Connection pool sized explicitly, `pool_pre_ping=True`
- [ ] Correct connection string — **check the port**, not just the host

### Ingestion
- [ ] Table extraction handled deliberately
- [ ] Chunk on structure, then token budget
- [ ] **No fallback that stores bad data** — raise instead
- [ ] Batched database writes
- [ ] Warn loudly on anything dropped
- [ ] Metadata stored **once**, referenced by FK
- [ ] **Read stored chunks back and look at them**

### Retrieval & agent
- [ ] Fetch wide, send narrow
- [ ] Small models for mechanical subtasks
- [ ] Request limit set from day one
- [ ] Citation registry per turn
- [ ] Fail-closed validation

### UI
- [ ] Loading, empty, and error state for every surface
- [ ] Citations clickable, showing neighbouring context
- [ ] Markdown with tables
- [ ] `aria-live` on status; `prefers-reduced-motion` respected
- [ ] Test dark mode if you ship it — images and stray palette colours

### Before deploying
- [ ] **Verify your verification** — does `tsc`/pytest actually check anything? Break something on purpose.
- [ ] Docker images built **and run** locally
- [ ] `.dockerignore` excludes secrets
- [ ] Health endpoints per service
- [ ] Heavy optional deps out of the runtime image
- [ ] Bind `0.0.0.0`, never set `PORT` yourself
- [ ] Build-time vs runtime variables understood
- [ ] Specific routes before catch-alls

### After deploying
- [ ] Health endpoints return the right thing
- [ ] CORS verified with a real preflight
- [ ] Build-time variables **verified in the shipped bundle**
- [ ] Auth redirect URLs updated
- [ ] Full flow tested in a real browser
- [ ] Costs re-checked after one real query

---

## The five lessons that mattered most

1. **Verify your verification.** A test suite running zero tests, a type-checker checking no files, a green tick that means nothing. Break something deliberately and confirm the tooling notices.

2. **A fallback producing bad data is worse than an error.** Failing loudly costs an hour. Failing silently cost us weeks of corrupted citations.

3. **Read your stored data.** Not the rendered output — the actual rows. The table corruption was plainly visible in the database while we debugged the display layer.

4. **When the user says it's still broken, believe them.** We patched a plausible cause, declared it fixed, and were wrong. The detail that disproved it was in their bug report all along. Reproduce before you fix.

5. **Know which layer the bug lives in.** Bad rendering of good data and good rendering of bad data look identical to a user, and have completely different fixes.
