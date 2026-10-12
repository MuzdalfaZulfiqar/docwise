from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://rag:rag@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"
    allow_registration: bool = True
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 25

    # LLM layer
    llm_chain: str = "fake:fake"  # "provider:model,provider:model" -> fallback order
    llm_timeout: float = 60.0
    llm_max_retries: int = 2
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""

    # embeddings
    embed_provider: str = "fake"  # openai | fake
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536  # must match vector(1536) in db/init.sql
    embed_batch_size: int = 64

    # chunking + retrieval (compared by the eval harness)
    chunk_strategy: str = "structure"  # fixed | sentence | structure
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_mode: str = "hybrid"  # vector | keyword | hybrid
    top_k: int = 6
    candidate_k: int = 30
    max_context_chars: int = 12000
    history_messages: int = 6

    # quotas
    default_daily_token_quota: int = 200_000
    default_max_documents: int = 50


settings = Settings()
