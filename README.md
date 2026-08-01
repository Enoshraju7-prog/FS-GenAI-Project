# Full-Stack GenAI Project

A full-stack AI-powered document Q&A application built with **FastAPI**, **React**, and **Supabase**.

Users can ask natural language questions and get answers grounded in hundreds of real SEC financial filings (Apple, Microsoft, Nvidia, Amazon, Google). The AI reads the documents and cites its sources — no hallucination, just evidence.

---

## What We're Building

**"Driftwood Capital"** — a fictional investment research firm where analysts need to search through years of company reports instantly.

Instead of reading 500-page PDFs manually, analysts type a question like:
> *"What were Apple's biggest risks in 2022?"*

…and the system finds the relevant parts of the actual filings and answers with citations.

This is called **RAG** (Retrieval-Augmented Generation) — a core AI engineering pattern used in real products.

---

## Tech Stack

| Layer | Technology | What it does |
|-------|-----------|-------------|
| Backend | **FastAPI** (Python) | API server — handles requests, runs AI logic |
| Frontend | **React + TypeScript** (Vite) | Chat interface users interact with |
| Database | **Supabase** (PostgreSQL + pgvector) | Stores documents and AI embeddings |
| AI | **OpenAI API** | Generates answers and creates embeddings |
| Document parsing | **Docling** | Converts messy HTML filings into clean chunks |
| Deployment | **Railway** | Hosts the backend in the cloud |
| UI Components | **shadcn/ui + Prompt Kit** | Pre-built chat UI components |

---

## Project Structure

```
FS-GenAI-Project/
├── backend/          # FastAPI Python backend
│   ├── app/          # API routes, auth, RAG logic
│   └── ingest/       # Document ingestion pipeline
├── frontend/         # React + TypeScript frontend
│   └── src/          # Components, pages, hooks
├── data/             # SEC filing downloader scripts
└── README.md
```

---

## Architecture Overview

```
[SEC EDGAR API]
      ↓ download HTM filings
[Docling] → chunk documents into sections
      ↓
[OpenAI Embeddings] → convert text to vectors
      ↓
[Supabase pgvector] → store chunks + vectors
      ↓
[FastAPI RAG endpoint] ← user question
      ↓ semantic search → retrieve top chunks
[OpenAI LLM] → generate answer with citations
      ↓
[React Chat UI] → display answer + sources
```

---

## Prerequisites

Before you start, install these tools:

- **Python 3.11+** — [python.org](https://python.org)
- **UV** — fast Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Node.js 20+** — [nodejs.org](https://nodejs.org)
- **pnpm** — fast Node package manager: `npm install -g pnpm`
- A **Supabase** account (free) — [supabase.com](https://supabase.com)
- An **OpenAI API** key — [platform.openai.com](https://platform.openai.com)

---

## Setup (Step by Step)

### 1. Clone the repo
```bash
git clone https://github.com/Enoshraju7-prog/FS-GenAI-Project.git
cd FS-GenAI-Project
```

### 2. Download SEC filings
```bash
cd data
uv run download.py
```
This downloads the last 5 years of 10-K/10-Q filings for Apple, Microsoft, Nvidia, Amazon, and Google.

### 3. Set up environment variables
```bash
# Backend
cp backend/.env.example backend/.env
# Fill in: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY

# Frontend
cp frontend/.env.example frontend/.env
# Fill in: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
```

### 4. Run the backend
```bash
cd backend
uv run uvicorn app.main:app --reload
```
API runs at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### 5. Run the ingestion pipeline
```bash
cd backend
uv run python ingest/pipeline.py
```
This chunks the documents, generates embeddings, and loads them into Supabase.

### 6. Run the frontend
```bash
cd frontend
pnpm install
pnpm dev
```
Opens at `http://localhost:5173`.

---

## Key Concepts Explained

### What is RAG?
RAG = **Retrieval-Augmented Generation**. Instead of asking an AI to answer from memory (which leads to hallucination), we first *retrieve* relevant document chunks from our database, then *generate* an answer using those chunks as context. The AI can only answer based on what's in the documents.

### What are embeddings?
An embedding is a list of numbers (a "vector") that represents the meaning of a piece of text. Similar meanings = similar vectors. This lets us search documents by meaning, not just keywords. Example: "annual revenue" and "yearly income" would have similar vectors even though the words differ.

### What is pgvector?
A Postgres extension that adds a special column type for storing vectors. Supabase includes it built-in. It lets you do "find the 5 most similar chunks to this question" as a single SQL query.

### What is Docling?
An open-source library by IBM that converts complex document formats (HTML, PDF) into clean, structured chunks that preserve tables, section headers, and page numbers — much better than simple text splitting.

---

## Sessions Progress

| Session | Topics Covered | Status |
|---------|---------------|--------|
| Session 1 | Project setup, overview, GitHub init | ✅ Done |

---

## Credits

Built by following [Dave Ebbelaar's tutorial](https://youtu.be/qF5il_9IwME).
All code written and maintained by [Enoshraju7-prog](https://github.com/Enoshraju7-prog).
