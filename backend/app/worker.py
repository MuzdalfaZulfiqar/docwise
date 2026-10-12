from arq.connections import RedisSettings

from . import db
from .config import settings
from .services.ingest import ingest_document


async def ingest_job(ctx, document_id: str):
    await ingest_document(document_id)


async def startup(ctx):
    await db.init_pool()


async def shutdown(ctx):
    await db.close_pool()


class WorkerSettings:
    functions = [ingest_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 4
    max_tries = 3
    job_timeout = 900
