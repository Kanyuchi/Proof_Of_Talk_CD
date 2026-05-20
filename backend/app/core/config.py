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
    AWS_SES_FROM_EMAIL: str = ""  # Verified SES sender address (legacy, use Resend)
    APP_PUBLIC_URL: str = "https://meet.proofoftalk.io"  # production frontend (was old AWS IP)

    # Resend (primary email provider)
    RESEND_API_KEY: str = ""
    # Send from the warm, established xventures.de domain (team@ is a real
    # monitored inbox that also RECEIVES, so replies don't bounce). Switch to
    # matchmaker@xventures.de once that mailbox/alias exists on Workspace.
    RESEND_FROM_EMAIL: str = "Proof of Talk <team@xventures.de>"
    # Reply-To so attendee replies land in a monitored inbox even if the
    # From address ever becomes send-only (e.g. matchmaker@). Blank = omit.
    EMAIL_REPLY_TO: str = "team@xventures.de"

    # Email gating — controls who actually receives mail. Safe default is
    # "off" so a deploy never sends until explicitly flipped via env var.
    #   off       — nothing sends (current behaviour, now config-driven)
    #   allowlist — only addresses in EMAIL_ALLOWLIST receive (team testing)
    #   all       — everyone receives (full rollout)
    # Rollout team→everyone is a Railway env-var change only, no redeploy.
    # Registration gate — when True, only people already in the attendees
    # table (bought a Rhuna ticket or added by ops/speaker-sheet) can create
    # a login. Blocks random non-ticket-holders from self-registering into
    # the pool. Kept as a flag so it can be flipped off via env if it locks
    # out a legitimate group (e.g. speakers whose row has a placeholder email).
    REQUIRE_TICKET_TO_REGISTER: bool = True

    EMAIL_MODE: str = "off"
    # Comma-separated; used when EMAIL_MODE=allowlist. Entries starting with
    # "@" match a whole domain (e.g. "@proofoftalk.io"), others are exact
    # addresses. For team testing: "@proofoftalk.io,@xventures.de".
    EMAIL_ALLOWLIST: str = ""

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    # 30 days — covers the multi-week pre-event window + the 2-day event
    # itself so attendees stay logged in across overnight gaps. Sliding-token
    # refresh in main.py further extends for active users. 8h (the previous
    # value) was kicking returning users out the next morning (Sithum,
    # 2026-05-17). Reset SECRET_KEY post-event to force everyone to re-auth.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # Integration (Runa / third-party)
    INTEGRATION_API_KEY: str = ""
    INTEGRATION_API_KEY_SECONDARY: str = ""  # For key rotation

    # Enrichment API keys (optional, for Level 3 data enrichment)
    PROXYCURL_API_KEY: str = ""  # LinkedIn enrichment (defunct — Proxycurl sunset)
    SCRAPIN_API_KEY: str = ""    # LinkedIn enrichment via Scrapin.io (paid, not currently used)
    TWITTER_BEARER_TOKEN: str = ""
    CRUNCHBASE_API_KEY: str = ""  # Crunchbase Basic API (optional)

    # LinkedIn — linkedin-api library (primary, free, uses your LinkedIn credentials)
    LINKEDIN_EMAIL: str = ""      # LinkedIn account email
    LINKEDIN_PASSWORD: str = ""   # LinkedIn account password

    # LinkedIn Voyager (Chrome DevTools session cookie — fallback if linkedin-api fails)
    LINKEDIN_LI_AT_COOKIE: str = ""   # li_at cookie value from Chrome DevTools
    LINKEDIN_CSRF_TOKEN: str = ""     # ajax:XXXXXXX part of JSESSIONID cookie

    # CORS – comma-separated list of allowed origins
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
