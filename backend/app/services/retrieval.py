"""Hybrid retrieval: pgvector cosine + Postgres full-text, fused with Reciprocal Rank Fusion.
EVERY query filters on user_id - this is the isolation boundary.
"""
import numpy as np

from .. import db
from ..config import settings

_COLS = "c.id, c.document_id, d.filename, c.idx, c.page, c.char_start, c.char_end, c.heading, c.text"

_VEC = f"""SELECT {_COLS} FROM chunks c JOIN documents d ON d.id = c.document_id
WHERE c.user_id = $1 AND ($4::uuid[] IS NULL OR c.document_id = ANY($4))
ORDER BY c.embedding <=> $2 LIMIT $3"""
# NOTE: with HNSW + a selective WHERE, results can be under-filled. If you see that,
# SET hnsw.iterative_scan = relaxed_order (pgvector >= 0.8) or raise ef_search.

_KW = f"""SELECT {_COLS} FROM chunks c JOIN documents d ON d.id = c.document_id,
     websearch_to_tsquery('english', $2) q
WHERE c.user_id = $1 AND c.tsv @@ q AND ($4::uuid[] IS NULL OR c.document_id = ANY($4))
ORDER BY ts_rank_cd(c.tsv, q) DESC LIMIT $3"""


def rrf(ranked_lists: list[list[dict]], k: int = 60) -> list[dict]:
    scores: dict[int, float] = {}
    by_id: dict[int, dict] = {}
    for lst in ranked_lists:
        for rank, row in enumerate(lst, start=1):
            scores[row["id"]] = scores.get(row["id"], 0.0) + 1.0 / (k + rank)
            by_id[row["id"]] = row
    return [{**by_id[i], "score": s} for i, s in sorted(scores.items(), key=lambda x: -x[1])]


async def retrieve(user_id, query: str, qvec, mode: str | None = None, top_k: int | None = None,
                   candidate_k: int | None = None, doc_ids: list | None = None) -> list[dict]:
    mode = mode or settings.retrieval_mode
    top_k = top_k or settings.top_k
    ck = candidate_k or settings.candidate_k
    lists = []
    if mode in ("vector", "hybrid"):
        rows = await db.pool.fetch(_VEC, user_id, np.asarray(qvec, dtype=np.float32), ck, doc_ids)
        lists.append([dict(r) for r in rows])
    if mode in ("keyword", "hybrid"):
        rows = await db.pool.fetch(_KW, user_id, query, ck, doc_ids)
        lists.append([dict(r) for r in rows])
    fused = rrf(lists)
    return rerank(query, fused)[:top_k]


def rerank(query: str, hits: list[dict]) -> list[dict]:
    """Hook for optional reranking (cross-encoder or LLM). Identity for now."""
    return hits
