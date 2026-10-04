# PrepMate

Personal AI interview coach for a friend preparing for SDE interviews — built from their resume, target role, and job description.

> **Status:** Candidate analysis MVP (PDF + JD → RAG → Gemma 2B JSON) plus a simple Analyze demo page. Interview engine is not implemented yet.

This project was started for the **Hacktoberfest 2026 DEV Challenge: Build for a Friend**.

## Problem

A friend targeting software-engineering interviews has a resume, a job description, and a long list of topics (DSA, OS, System Design, languages). Generic chatbots do not ground questions in *this* resume and *this* JD, track skill gaps, or adapt the next question to weak answers.

## Solution

PrepMate will analyze the resume and JD, surface skill gaps, run an adaptive mock interview with an open-weight model, and produce a report plus a short study plan.

## Architecture (planned)

```
Browser (Next.js)
        |
        v
FastAPI backend
        |
        +-- PDF extraction
        +-- Embeddings + FAISS (RAG)
        +-- Open-weight LLM (Gemma via Ollama)
        +-- Adaptive interview engine
        +-- Report generator
        +-- SQLite session history (no resume files kept)
```

## Open-weight AI (MVP)

- **Model:** `gemma2:2b` through **Ollama** (local, free, no paid API).
- **Why 2B for MVP:** it is practical on a normal laptop. Switch later with `LLM_MODEL` (for example `gemma2:9b`) without code changes.
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (open, local).

If Ollama is used, inference stays on the developer’s machine. We will not claim local-only processing if a remote provider is configured.

## Project structure

```
PrepMate/
  backend/     FastAPI app (to be implemented)
  frontend/    Next.js + TypeScript + Tailwind (to be implemented)
  sample/      Clearly labeled synthetic demo data
  .env.example Environment variable template
  .gitignore
  README.md
```

## Local setup

1. Copy `.env.example` to `.env`

### Running backend (Phase 3)

From `backend/`:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Extract text from the labeled demo PDF (file is not saved on disk):

```bash
curl -X POST http://127.0.0.1:8000/documents/extract -F "file=@../sample/demo_resume.pdf;type=application/pdf" -F "document_type=resume"
```

PDF extraction tests:

```bash
python -m pytest -q
```

Optional local LLM smoke test (requires Ollama + `ollama pull gemma2:2b`):

```bash
curl -X POST http://127.0.0.1:8000/llm/generate -H "Content-Type: application/json" -d "{\"prompt\":\"Reply with the word ready.\"}"
```

Ollama is not required for unit tests. The first RAG test downloads `all-MiniLM-L6-v2` into the local Hugging Face cache (free, no API key).

### Running frontend (analysis demo)

From `frontend/`:

```bash
copy .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`, upload `sample/demo_resume.pdf`, paste `sample/job_description.txt`, click **Analyze My Fit**. The backend must be running on port 8000 with Ollama + `gemma2:2b` for a live analysis.

## Privacy

Resumes are sensitive. The planned design extracts text in memory, does not permanently store uploaded PDFs, and lets users delete interview sessions. Details will be documented when those features exist.

## Hacktoberfest 2026

This project is being built for the Hacktoberfest 2026 DEV Challenge: **Build for a Friend**.
