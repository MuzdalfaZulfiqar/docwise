from arq import create_pool
from arq.connections import RedisSettings

from .config import settings

_pool = None


async def enqueue_ingest(document_id: str):
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await _pool.enqueue_job("ingest_job", document_id)
