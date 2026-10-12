"""Thin provider-agnostic streaming LLM wrapper: timeouts, retries, fallback chain.

stream_chat yields dicts:
  {"type": "token", "text": str, "model": str}
  {"type": "usage", "input_tokens": int, "output_tokens": int, "model": str}
Fallback only happens BEFORE the first token; a mid-stream failure is raised.
"""
import asyncio
import json
from typing import AsyncIterator

import httpx

from ..config import settings


class LLMError(Exception):
    pass


class LLMHTTPError(Exception):
    def __init__(self, provider: str, status: int, body: str):
        super().__init__(f"{provider} returned {status}: {body[:300]}")
        self.status = status


async def _check(r: httpx.Response, provider: str):
    if r.status_code >= 400:
        raise LLMHTTPError(provider, r.status_code, (await r.aread()).decode("utf-8", "replace"))


def _timeout():
    return httpx.Timeout(settings.llm_timeout, connect=5.0)


async def _openai(model: str, system: str, messages: list[dict]) -> AsyncIterator[dict]:
    payload = {
        "model": model, "stream": True,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    if "googleapis.com" not in settings.openai_base_url:  # Gemini 3.x: keep Google's default temperature
        payload["temperature"] = 0.1
    if "api.openai.com" in settings.openai_base_url:  # other OpenAI-compatible hosts may reject this field
        payload["stream_options"] = {"include_usage": True}
    usage = {"input_tokens": 0, "output_tokens": 0}
    out_text = ""
    async with httpx.AsyncClient(timeout=_timeout()) as c:
        async with c.stream("POST", f"{settings.openai_base_url}/chat/completions",
                            headers={"Authorization": f"Bearer {settings.openai_api_key}"}, json=payload) as r:
            await _check(r, "openai-compatible API")
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                j = json.loads(data)
                if j.get("usage"):
                    usage = {"input_tokens": j["usage"]["prompt_tokens"], "output_tokens": j["usage"]["completion_tokens"]}
                for ch in j.get("choices", []):
                    t = (ch.get("delta") or {}).get("content")
                    if t:
                        out_text += t
                        yield {"type": "token", "text": t}
    if not usage["input_tokens"] and not usage["output_tokens"]:  # provider sent no usage: estimate
        usage = {"input_tokens": (len(system) + sum(len(m["content"]) for m in messages)) // 4,
                 "output_tokens": len(out_text) // 4}
    yield {"type": "usage", **usage}


async def _anthropic(model: str, system: str, messages: list[dict]) -> AsyncIterator[dict]:
    payload = {"model": model, "max_tokens": 1024, "system": system, "messages": messages, "stream": True, "temperature": 0.1}
    usage = {"input_tokens": 0, "output_tokens": 0}
    headers = {"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"}
    async with httpx.AsyncClient(timeout=_timeout()) as c:
        async with c.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload) as r:
            await _check(r, "anthropic")
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                j = json.loads(line[6:])
                t = j.get("type")
                if t == "message_start":
                    usage["input_tokens"] = j["message"]["usage"]["input_tokens"]
                elif t == "content_block_delta" and j["delta"].get("type") == "text_delta":
                    yield {"type": "token", "text": j["delta"]["text"]}
                elif t == "message_delta":
                    usage["output_tokens"] = j["usage"]["output_tokens"]
    yield {"type": "usage", **usage}


async def _fake(model: str, system: str, messages: list[dict]) -> AsyncIterator[dict]:
    text = "This is a fake offline answer based on the provided sources [1]."
    for word in text.split(" "):
        yield {"type": "token", "text": word + " "}
        await asyncio.sleep(0)
    yield {"type": "usage", "input_tokens": (len(system) + sum(len(m["content"]) for m in messages)) // 4,
           "output_tokens": len(text) // 4}


PROVIDERS = {"openai": _openai, "anthropic": _anthropic, "fake": _fake}


async def stream_chat(system: str, messages: list[dict]) -> AsyncIterator[dict]:
    errors: list[str] = []
    for spec in settings.llm_chain.split(","):
        provider, _, model = spec.strip().partition(":")
        model = model or provider
        for attempt in range(settings.llm_max_retries + 1):
            started = False
            try:
                async for ev in PROVIDERS[provider](model, system, messages):
                    started = started or ev["type"] == "token"
                    yield {**ev, "model": model}
                return
            except Exception as e:
                errors.append(f"{provider}:{model} -> {e}")
                if started:
                    raise LLMError(f"stream interrupted: {e}") from e
                if isinstance(e, LLMHTTPError) and e.status in (400, 401, 403, 404):
                    break  # retrying won't help; move on to the next model in the chain
                await asyncio.sleep(min(2 ** attempt, 8) * 0.5)
    raise LLMError("All models failed. " + " | ".join(errors[-3:]))


async def complete(system: str, messages: list[dict]) -> tuple[str, dict]:
    """Non-streaming helper (eval judge etc.). Returns (text, usage)."""
    text, usage = "", {}
    async for ev in stream_chat(system, messages):
        if ev["type"] == "token":
            text += ev["text"]
        else:
            usage = ev
    return text, usage