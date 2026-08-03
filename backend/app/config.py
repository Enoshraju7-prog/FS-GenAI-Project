from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase (Auth + API)
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Postgres — direct/session connection for Alembic and raw DB access.
    # Pool defaults (5 + 10 overflow) are too small for the ~40-analyst pilot, since
    # every retrieval turn holds a connection while it runs blocking SQL in a thread.
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # OpenAI
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    # gpt-4.1 is rate-limited to 30k TPM on this account — 16x below the gpt-5 family's
    # 500k — and a turn with neighbours inlined blows through that mid-run. Measured
    # 2026-08-03 from x-ratelimit-limit-tokens, not assumed.
    openai_chat_model: str = "gpt-5"
    openai_grounding_model: str = "gpt-4.1-mini"
    # Each agent iteration re-sends the whole conversation, so this caps cost as much as
    # latency. Multi-part questions ("demand drivers, customer concentration, and supply
    # constraints") need several search/read rounds; 8 cut them off mid-run.
    openai_agent_request_limit: int = 20
    openai_agent_temperature: float = 0.0
    # Rate limits are per-minute and this account's gpt-4.1 tier is small, so a busy
    # turn will hit 429 mid-run. The SDK honours Retry-After; these just give it room.
    openai_max_retries: int = 5
    openai_timeout_seconds: float = 120.0

    # Retrieval (hybrid search)
    retrieval_candidate_k: int = 50
    # 10, not 5: with a cheaper chat model, answer breadth has to come from seeing more
    # passages per search. 5 was half of what the agent needs on multi-part questions.
    retrieval_top_k: int = 10
    retrieval_rrf_k: int = 60
    retrieval_neighbor_radius: int = 1
    retrieval_fts_config: str = "english"
    retrieval_fts_keyword_model: str = "gpt-4.1-mini"
    retrieval_fts_keyword_min: int = 3
    retrieval_fts_keyword_max: int = 5
    retrieval_fts_keyword_fast_path_tokens: int = 5

    # Logging — JSON in deployed environments, human-readable locally.
    log_level: str = "INFO"
    log_json: bool = False

    # Comma-separated in .env; use `cors_origins` for the parsed list.
    allowed_origins: str = "http://localhost:5173"

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @computed_field
    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize Supabase-style URLs for SQLAlchemy + psycopg v3."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
