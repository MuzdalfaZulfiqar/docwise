from fastapi import HTTPException

from .. import db


async def tokens_used_today(user_id) -> int:
    return await db.pool.fetchval(
        "SELECT COALESCE(SUM(input_tokens + output_tokens + embed_tokens), 0) FROM usage_log"
        " WHERE user_id = $1 AND created_at >= date_trunc('day', now())", user_id)


async def check_chat_quota(user: dict):
    used = await tokens_used_today(user["id"])
    if used >= user["daily_token_quota"]:
        raise HTTPException(429, f"Daily token quota reached ({used}/{user['daily_token_quota']}).")


async def check_doc_quota(user: dict):
    n = await db.pool.fetchval("SELECT count(*) FROM documents WHERE user_id = $1", user["id"])
    if n >= user["max_documents"]:
        raise HTTPException(429, f"Document limit reached ({user['max_documents']}).")
