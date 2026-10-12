import hashlib
import re

import httpx
import numpy as np

from .. import db
from ..config import settings
from .vectors import parse_embeddings


def _fake_embed(text: str) -> np.ndarray:
    """Deterministic bag-of-words hashing embedding. Offline dev/tests/CI only."""
    v = np.zeros(settings.embed_dim, dtype=np.float32)
    for tok in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % settings.embed_dim] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


async def _openai_embed(texts: list[str]) -> tuple[list[np.ndarray], int]:
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"{settings.openai_base_url}/embeddings",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": settings.embed_model, "input": texts, "dimensions": settings.embed_dim},
        )
    if r.status_code >= 400:  # surface the provider's message (bad key, wrong model name, rate limit...)
        raise RuntimeError(f"Embedding API error {r.status_code}: {r.text[:300]}")
    return parse_embeddings(r.json(), texts, settings.embed_dim)


def _to_np(v) -> np.ndarray:
    # pgvector returns a Vector object (newer versions) or a list/array (older ones)
    return v.to_numpy() if hasattr(v, "to_numpy") else np.asarray(v, dtype=np.float32)


def _key(text: str) -> str:
    return hashlib.sha256(f"{settings.embed_provider}:{settings.embed_model}:{text}".encode()).hexdigest()


async def embed_texts(texts: list[str]) -> tuple[list[np.ndarray], int]:
    """Embed with a DB cache. Returns (vectors in input order, billable tokens actually used)."""
    keys = [_key(t) for t in texts]
    rows = await db.pool.fetch("SELECT hash, embedding FROM embedding_cache WHERE hash = ANY($1)", keys)
    found = {r["hash"]: _to_np(r["embedding"]) for r in rows}

    missing: dict[str, str] = {}
    for k, t in zip(keys, texts):
        if k not in found:
            missing[k] = t
    tokens = 0
    items = list(missing.items())
    for i in range(0, len(items), settings.embed_batch_size):
        batch = items[i : i + settings.embed_batch_size]
        if settings.embed_provider == "fake":
            vecs, tok = [_fake_embed(t) for _, t in batch], sum(len(t) // 4 for _, t in batch)
        else:
            vecs, tok = await _openai_embed([t for _, t in batch])
        tokens += tok
        await db.pool.executemany(
            "INSERT INTO embedding_cache (hash, embedding) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            [(k, v) for (k, _), v in zip(batch, vecs)],
        )
        for (k, _), v in zip(batch, vecs):
            found[k] = v
    return [found[k] for k in keys], tokens
