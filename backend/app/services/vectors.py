"""Pure helpers for turning an embeddings API response into vectors the DB accepts."""
import numpy as np


def fit_dim(v, dim: int) -> np.ndarray:
    """Gemini/OpenAI 'large' models can return more dims than requested. They are trained so that
    the leading dims are meaningful (Matryoshka), so truncating + re-normalising is the standard fix."""
    arr = np.asarray(v, dtype=np.float32)
    n = arr.shape[0]
    if n == dim:
        return arr
    if n > dim:
        arr = arr[:dim]
        norm = np.linalg.norm(arr)
        return arr / norm if norm else arr
    raise ValueError(f"Embedding model returned {n} dimensions but the database expects {dim}. "
                     f"Pick a model with at least {dim} dims or change EMBED_DIM and db/init.sql together.")


def parse_embeddings(j: dict, texts: list[str], dim: int) -> tuple[list[np.ndarray], int]:
    data = j.get("data") or []
    # OpenAI includes "index"; Gemini's compatibility endpoint does not. Keep API order if missing.
    if data and all("index" in d for d in data):
        data = sorted(data, key=lambda d: d["index"])
    vecs = [fit_dim(d["embedding"], dim) for d in data]
    if len(vecs) != len(texts):
        raise ValueError(f"Embedding API returned {len(vecs)} vectors for {len(texts)} inputs.")
    tokens = (j.get("usage") or {}).get("total_tokens") or sum(len(t) for t in texts) // 4
    return vecs, tokens
