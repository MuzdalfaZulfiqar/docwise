# USD per 1M tokens. VERIFY against current provider pricing before trusting cost numbers.
LLM_PRICES = {  # model: (input, output)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "fake": (0.0, 0.0),
}
EMBED_PRICES = {"text-embedding-3-small": 0.02, "text-embedding-3-large": 0.13, "fake": 0.0}


def llm_cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = LLM_PRICES.get(model, (0.0, 0.0))
    return (in_tok * pin + out_tok * pout) / 1_000_000


def embed_cost(model: str, tokens: int) -> float:
    return tokens * EMBED_PRICES.get(model, 0.0) / 1_000_000
