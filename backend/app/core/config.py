from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "POT Matchmaker"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database (AWS RDS PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/pot_matchmaker"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_AGENT_MODEL: str = "gpt-4o-mini"
    OPENAI_REASONING_MODEL: str = "gpt-4o"
    OPENAI_RERANK_MODEL: str = "gpt-4o"
    AI_AGENT_ENABLED: bool = False
    AI_RERANK_ENABLED: bool = False
    AI_CONFIDENCE_ENABLED: bool = True
    AI_NUDGE_ENABLED: bool = False

    # Matching runtime controls
    MATCH_BATCH_SIZE: int = 100
    MATCH_MAX_CONCURRENCY: int = 4

    # AWS
    AWS_REGION: str = "eu-west-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Enrichment API keys (optional, for Level 3 data enrichment)
    PROXYCURL_API_KEY: str = ""  # LinkedIn enrichment
    TWITTER_BEARER_TOKEN: str = ""
    CRUNCHBASE_API_KEY: str = ""  # Crunchbase Basic API (optional)

    # CORS – comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
