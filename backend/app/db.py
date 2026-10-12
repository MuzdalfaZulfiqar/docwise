import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg
from pgvector.asyncpg import register_vector

from .config import settings

pool: asyncpg.Pool | None = None


def _clean_dsn(dsn: str) -> str:
    """Neon's copy-paste URL can include channel_binding=require, which asyncpg would forward to the
    server as an unknown setting and fail. Drop it; sslmode=require is kept and understood."""
    parts = urlsplit(dsn)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    return urlunsplit(parts._replace(query=urlencode(query)))


async def _init(conn: asyncpg.Connection):
    await register_vector(conn)
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def init_pool():
    global pool
    pool = await asyncpg.create_pool(
        _clean_dsn(settings.database_url),
        init=_init,
        min_size=1,
        max_size=10,
        statement_cache_size=0,  # needed behind PgBouncer (Neon's pooled endpoint); harmless elsewhere
        max_inactive_connection_lifetime=30,  # Neon suspends idle compute; don't hold dead connections
    )


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None
