import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import db
from ..config import settings
from ..deps import current_user
from ..services.cost import embed_cost, llm_cost
from ..services.embeddings import embed_texts
from ..services.llm import LLMError, stream_chat
from ..services.prompts import REFUSAL, SYSTEM_PROMPT, build_context, build_user_prompt
from ..services.quotas import check_chat_quota
from ..services.retrieval import retrieve

router = APIRouter(tags=["chat"])


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    document_ids: list[UUID] | None = None


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get("/conversations")
async def conversations(user: dict = Depends(current_user)):
    rows = await db.pool.fetch(
        "SELECT id, title, created_at FROM conversations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50", user["id"])
    return [dict(r) for r in rows]


@router.get("/conversations/{cid}/messages")
async def messages(cid: UUID, user: dict = Depends(current_user)):
    if not await db.pool.fetchval("SELECT 1 FROM conversations WHERE id = $1 AND user_id = $2", cid, user["id"]):
        raise HTTPException(404, "Conversation not found")
    rows = await db.pool.fetch("SELECT role, content, sources, created_at FROM messages WHERE conversation_id = $1 ORDER BY id", cid)
    return [dict(r) for r in rows]


@router.post("/chat")
async def chat(body: ChatIn, user: dict = Depends(current_user)):
    await check_chat_quota(user)

    cid = body.conversation_id
    if cid:
        if not await db.pool.fetchval("SELECT 1 FROM conversations WHERE id = $1 AND user_id = $2", cid, user["id"]):
            raise HTTPException(404, "Conversation not found")
    else:
        cid = await db.pool.fetchval(
            "INSERT INTO conversations (user_id, title) VALUES ($1, $2) RETURNING id", user["id"], body.question[:60])
    hist_rows = await db.pool.fetch(
        "SELECT role, content FROM messages WHERE conversation_id = $1 ORDER BY id DESC LIMIT $2", cid, settings.history_messages)
    history = [{"role": r["role"], "content": r["content"]} for r in reversed(hist_rows)]
    await db.pool.execute("INSERT INTO messages (conversation_id, role, content) VALUES ($1,'user',$2)", cid, body.question)

    async def stream():
        t0 = time.perf_counter()
        yield sse("meta", {"conversation_id": str(cid)})
        try:
            qvecs, embed_tokens = await embed_texts([body.question])
            hits = build_context(
                await retrieve(user["id"], body.question, qvecs[0], doc_ids=body.document_ids), settings.max_context_chars)
        except Exception as e:
            yield sse("error", {"message": f"Couldn't search your documents. {str(e)[:300]}"})
            return
        sources = [{"n": n, "chunk_id": h["id"], "document_id": str(h["document_id"]), "filename": h["filename"],
                    "page": h["page"], "char_start": h["char_start"], "char_end": h["char_end"],
                    "heading": h["heading"], "snippet": h["text"][:240]} for n, h in enumerate(hits, start=1)]
        yield sse("sources", sources)

        answer, in_tok, out_tok, model = "", 0, 0, "none"
        if not hits:  # no evidence -> refuse without spending LLM tokens
            answer = REFUSAL
            yield sse("token", {"text": answer})
        else:
            msgs = [*history, {"role": "user", "content": build_user_prompt(body.question, hits)}]
            try:
                async for ev in stream_chat(SYSTEM_PROMPT, msgs):
                    model = ev["model"]
                    if ev["type"] == "token":
                        answer += ev["text"]
                        yield sse("token", {"text": ev["text"]})
                    else:
                        in_tok, out_tok = ev["input_tokens"], ev["output_tokens"]
            except LLMError as e:
                yield sse("error", {"message": str(e)})
                return

        cost = llm_cost(model, in_tok, out_tok) + embed_cost(settings.embed_model, embed_tokens)
        latency = int((time.perf_counter() - t0) * 1000)
        await db.pool.execute("INSERT INTO messages (conversation_id, role, content, sources) VALUES ($1,'assistant',$2,$3)",
                              cid, answer, sources)
        await db.pool.execute(
            "INSERT INTO usage_log (user_id, kind, model, input_tokens, output_tokens, embed_tokens, cost_usd, latency_ms)"
            " VALUES ($1,'chat',$2,$3,$4,$5,$6,$7)", user["id"], model, in_tok, out_tok, embed_tokens, cost, latency)
        yield sse("done", {"input_tokens": in_tok, "output_tokens": out_tok, "embed_tokens": embed_tokens,
                           "cost_usd": round(cost, 6), "latency_ms": latency, "model": model})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
