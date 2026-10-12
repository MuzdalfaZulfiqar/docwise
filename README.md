<!-- # RAG Document Assistant

Upload PDFs/notes, chat with them, get **streamed answers with clickable citations** — private per user,
quota-limited, cost-tracked, and evaluated.

## Quickstart

```bash
cp .env.example .env          # offline mode: set EMBED_PROVIDER=fake and LLM_CHAIN=fake:fake
docker compose up --build     # db + redis + api (:8000) + worker + frontend (:3000)
```
Open http://localhost:3000 → register → upload a file → watch status/progress → ask questions → click `[1]`.
API docs: http://localhost:8000/docs

Without Docker: run Postgres(pgvector)+Redis, `psql -f db/init.sql`, then in `backend/`:
`pip install -r requirements-dev.txt && uvicorn app.main:app --reload` and `arq app.worker.WorkerSettings`.

## Architecture

```
Next.js ──(JWT, SSE)──> FastAPI ──> Postgres + pgvector (users, docs, chunks, usage)
                           │
                           └─enqueue─> Redis ──> ARQ worker: parse → chunk → embed(cache, batched) → store
```

| Concern | Where |
|---|---|
| Isolation | `user_id` on every table; `retrieval.py` filters on it in every query; 404 not 403 for foreign docs |
| Ingestion + status | `routers/documents.py`, `services/ingest.py`, `worker.py` (status/progress columns, polled by UI) |
| Chunking (3 strategies) | `services/chunking.py` |
| Hybrid search (RRF) | `services/retrieval.py` (+ `rerank()` hook) |
| Hallucination control | `services/prompts.py` (answer-only-from-context, exact refusal string, no-hits ⇒ refuse w/o LLM call) |
| Prompt-injection defence | doc text escaped + wrapped in `<sources>`, system prompt marks it untrusted |
| LLM layer | `services/llm.py` (timeouts, retries, fallback chain via `LLM_CHAIN`) |
| Cost + quotas | `services/cost.py`, `quotas.py`, `usage_log` table, `done` SSE event carries tokens/$/latency |
| Eval | `backend/eval/` |

### SSE protocol (`POST /chat`)
`meta {conversation_id}` → `sources [...]` → `token {text}`* → `done {tokens, cost_usd, latency_ms, model}` (or `error`).

## Evaluation

```bash
cd backend
python -m eval.run_eval --strategy structure --mode hybrid           # one config
python -m eval.run_eval --strategy structure --mode hybrid --faithfulness   # + LLM-judge (real LLM)
python -m eval.run_all                                               # 3 chunkers x 3 retrieval modes
```
Results append to `backend/eval/results.md`. **Paste the table here once you have real-embedding numbers:**

| chunking | size/overlap | retrieval | embeddings | chunks | hit@6 | MRR | faithfulness | refusal |
|---|---|---|---|---|---|---|---|---|
| _TODO_ | | | | | | | | |

Replace the sample `eval/docs` + `dataset.jsonl` with your own real documents (aim for 30–50 questions,
including ~20% unanswerable ones) — the 10-question sample is only a smoke test.

## Tests
`make test` — chunking invariants, prompt-injection escaping, and integration tests (cross-user isolation,
quota enforcement, refusal-without-evidence). CI also runs the eval as a hit-rate regression gate.

## Roadmap / known gaps
- [ ] Real reranker (cross-encoder or LLM) behind `rerank()`; report with/without in the table
- [ ] Condense follow-up questions into standalone queries before retrieval
- [ ] OCR for scanned PDFs; PDF viewer jump-to-page (passage modal exists today)
- [ ] Rate limiting per minute (daily token quota exists), Alembic migrations, structured logging
- [ ] Deploy: API + worker images → Fly/Render/Railway/ECS; managed Postgres with pgvector (Neon/Supabase/RDS); object storage instead of local volume -->
