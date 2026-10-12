import asyncio

from .. import db
from ..config import settings
from .chunking import chunk_text
from .cost import embed_cost
from .embeddings import embed_texts
from .parsing import parse_file


async def _status(doc_id, status, **fields):
    sets = ["status = $2"] + [f"{k} = ${i + 3}" for i, k in enumerate(fields)]
    await db.pool.execute(f"UPDATE documents SET {', '.join(sets)} WHERE id = $1", doc_id, status, *fields.values())


async def ingest_document(document_id: str, strategy: str | None = None):
    """parse -> chunk -> embed (batched, cached) -> store. Idempotent: safe to retry."""
    doc = await db.pool.fetchrow("SELECT * FROM documents WHERE id = $1", document_id)
    if not doc:
        return
    strategy = strategy or settings.chunk_strategy
    doc_id, user_id = doc["id"], doc["user_id"]
    try:
        await _status(doc_id, "parsing", progress=5, error=None, chunk_strategy=strategy)
        pages = await asyncio.to_thread(parse_file, doc["storage_path"])
        chunks = []
        for page_no, text in pages:
            chunks += chunk_text(text, page_no, strategy, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise ValueError("No extractable text (scanned PDF? OCR is not supported yet).")

        await _status(doc_id, "embedding", progress=20, pages=len(pages), chunk_count=len(chunks))
        await db.pool.execute("DELETE FROM chunks WHERE document_id = $1", doc_id)

        total_tokens, B = 0, settings.embed_batch_size
        for i in range(0, len(chunks), B):
            batch = chunks[i : i + B]
            vecs, tok = await embed_texts([c.embed_text for c in batch])
            total_tokens += tok
            await db.pool.executemany(
                "INSERT INTO chunks (document_id, user_id, idx, text, page, char_start, char_end, heading, embedding)"
                " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
                [(doc_id, user_id, i + j, c.text, c.page, c.start, c.end, c.heading, v)
                 for j, (c, v) in enumerate(zip(batch, vecs))],
            )
            await _status(doc_id, "embedding", progress=20 + int(75 * (i + len(batch)) / len(chunks)))

        await db.pool.execute(
            "INSERT INTO usage_log (user_id, kind, model, embed_tokens, cost_usd) VALUES ($1,'embed_ingest',$2,$3,$4)",
            user_id, settings.embed_model, total_tokens, embed_cost(settings.embed_model, total_tokens),
        )
        await _status(doc_id, "ready", progress=100)
    except Exception as e:  # mark failed; don't re-raise (avoids pointless queue retries on bad files)
        await _status(doc_id, "failed", error=str(e)[:500])
