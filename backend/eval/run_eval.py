"""Eval harness: ingest eval/docs under a given chunking strategy, then score
 - hit@k   : is the gold evidence substring inside a retrieved chunk of the right doc?
 - MRR     : reciprocal rank of the first such chunk
 - faithfulness (optional --faithfulness, needs a real LLM): LLM-judge, is the answer supported by context?
 - refusal : on unanswerable questions, did the system refuse instead of answering? (needs --faithfulness)

Usage (from backend/):
  python -m eval.run_eval --strategy structure --mode hybrid [--faithfulness] [--min-hit 0.5]
Appends a row to eval/results.md so every config change leaves a number behind.
"""
import argparse
import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

from app import db
from app.config import settings
from app.services.embeddings import embed_texts
from app.services.ingest import ingest_document
from app.services.llm import complete
from app.services.prompts import REFUSAL, SYSTEM_PROMPT, build_context, build_user_prompt
from app.services.retrieval import retrieve

HERE = Path(__file__).parent
norm = lambda s: " ".join(s.split()).lower()  # noqa: E731


async def judge(question: str, answer: str, hits: list[dict]) -> float:
    ctx = "\n\n".join(h["text"] for h in hits)
    prompt = (f"CONTEXT:\n{ctx}\n\nQUESTION: {question}\n\nANSWER: {answer}\n\n"
              'Is every factual claim in ANSWER supported by CONTEXT? Reply ONLY with JSON: {"score": <0.0-1.0>}')
    text, _ = await complete("You are a strict evaluator of faithfulness.", [{"role": "user", "content": prompt}])
    m = re.search(r"[01](?:\.\d+)?", text)
    return float(m.group()) if m else 0.0


async def main(a):
    await db.init_pool()
    settings.chunk_size, settings.chunk_overlap = a.chunk_size, a.chunk_overlap
    uid = await db.pool.fetchval(
        "INSERT INTO users (email, password_hash) VALUES ($1, 'x') RETURNING id", f"eval-{uuid.uuid4().hex[:8]}@eval.local")
    try:
        doc_ids = {}
        for p in sorted((HERE / "docs").glob("*")):
            did = uuid.uuid4()
            await db.pool.execute("INSERT INTO documents (id, user_id, filename, storage_path) VALUES ($1,$2,$3,$4)",
                                  did, uid, p.name, str(p))
            await ingest_document(str(did), strategy=a.strategy)
            row = await db.pool.fetchrow("SELECT status, error, chunk_count FROM documents WHERE id = $1", did)
            if row["status"] != "ready":
                sys.exit(f"ingest failed for {p.name}: {row['error']}")
            doc_ids[p.name] = did
        n_chunks = await db.pool.fetchval("SELECT count(*) FROM chunks WHERE user_id = $1", uid)

        rows = [json.loads(line) for line in (HERE / "dataset.jsonl").read_text().splitlines() if line.strip()]
        hits_at_k, rr, faith, refusals, n_ans, n_unans = 0, 0.0, [], 0, 0, 0
        for r in rows:
            qv, _ = await embed_texts([r["question"]])
            hits = await retrieve(uid, r["question"], qv[0], mode=a.mode, top_k=a.k)
            if r["answerable"]:
                n_ans += 1
                ev = norm(r["evidence"])
                rank = next((i for i, h in enumerate(hits, 1) if h["filename"] == r["doc"] and ev in norm(h["text"])), None)
                hits_at_k += rank is not None
                rr += 1 / rank if rank else 0
            else:
                n_unans += 1
            if a.faithfulness:
                ctx = build_context(hits, settings.max_context_chars)
                if not ctx:
                    ans = REFUSAL
                else:
                    ans, _ = await complete(SYSTEM_PROMPT, [{"role": "user", "content": build_user_prompt(r["question"], ctx)}])
                if r["answerable"]:
                    faith.append(await judge(r["question"], ans, ctx))
                else:
                    refusals += REFUSAL.lower()[:20] in ans.lower()

        hit = hits_at_k / n_ans
        mrr = rr / n_ans
        f = f"{sum(faith) / len(faith):.2f}" if faith else "n/a"
        ref = f"{refusals / n_unans:.2f}" if a.faithfulness and n_unans else "n/a"
        row = (f"| {a.strategy} | {a.chunk_size}/{a.chunk_overlap} | {a.mode} | {settings.embed_provider}:{settings.embed_model} "
               f"| {n_chunks} | {hit:.2f} | {mrr:.2f} | {f} | {ref} |")
        head = ("| chunking | size/overlap | retrieval | embeddings | chunks | hit@%d | MRR | faithfulness | refusal |\n"
                "|---|---|---|---|---|---|---|---|---|\n" % a.k)
        out = HERE / "results.md"
        if not out.exists():
            out.write_text(head)
        with out.open("a") as fh:
            fh.write(row + "\n")
        print(head + row)
        if a.min_hit and hit < a.min_hit:
            sys.exit(f"hit@k {hit:.2f} below threshold {a.min_hit}")
    finally:
        await db.pool.execute("DELETE FROM users WHERE id = $1", uid)  # cascades docs + chunks + usage
        await db.close_pool()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default=settings.chunk_strategy, choices=["fixed", "sentence", "structure"])
    ap.add_argument("--mode", default=settings.retrieval_mode, choices=["vector", "keyword", "hybrid"])
    ap.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    ap.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    ap.add_argument("-k", type=int, default=settings.top_k)
    ap.add_argument("--faithfulness", action="store_true")
    ap.add_argument("--min-hit", type=float, default=0.0)
    asyncio.run(main(ap.parse_args()))
