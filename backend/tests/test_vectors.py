import numpy as np
import pytest

from app.services.vectors import fit_dim, parse_embeddings


def test_response_without_index_keeps_api_order():  # the exact Gemini shape that crashed
    j = {"data": [{"embedding": [1.0, 0.0, 0.0]}, {"embedding": [0.0, 1.0, 0.0]}]}
    vecs, tokens = parse_embeddings(j, ["a", "b"], 3)
    assert vecs[0][0] == 1.0 and vecs[1][1] == 1.0 and tokens >= 0


def test_response_with_index_is_sorted():  # the OpenAI shape
    j = {"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}],
         "usage": {"total_tokens": 7}}
    vecs, tokens = parse_embeddings(j, ["a", "b"], 2)
    assert vecs[0][0] == 1.0 and tokens == 7


def test_too_many_dims_are_truncated_and_normalised():  # Gemini returning 3072 for a 1536 column
    v = fit_dim(np.ones(3072), 1536)
    assert v.shape == (1536,) and abs(np.linalg.norm(v) - 1.0) < 1e-5


def test_too_few_dims_is_a_clear_error():
    with pytest.raises(ValueError, match="expects 1536"):
        fit_dim(np.ones(768), 1536)


def test_count_mismatch_is_an_error():
    with pytest.raises(ValueError):
        parse_embeddings({"data": [{"embedding": [1.0]}]}, ["a", "b"], 1)
