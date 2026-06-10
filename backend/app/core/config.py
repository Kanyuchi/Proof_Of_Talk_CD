from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "POT Matchmaker"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database (Supabase PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/pot_matchmaker"
    # Connection-pool sizing per worker. Prod runs on the transaction-mode
    # POOLER (…:6543) since the 2026-05-28 forced Supabase migration, so
    # pgbouncer multiplexes and these can be larger than they were for the
    # direct connection. Bumped 5/10 → 20/30 on 2026-05-29 after
    # daily_extasy_sync hit "QueuePool limit of size 5 overflow 10 reached"
    # on a 57-attendee enrichment loop; ceiling is now 50 concurrent.
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30

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

    # Sponsor self-service invite. Blank = feature OFF (the /join endpoint and
    # the /join/<code> page both refuse). Set to an unguessable string
    # (e.g. `python -c "import secrets;print(secrets.token_urlsafe(24))"`) in
    # Railway env, then share https://meet.proofoftalk.io/join/<code>. Anyone
    # with the link self-registers a full SPONSOR account; rotating this value
    # revokes the old link.
    SPONSOR_INVITE_CODE: str = ""

    # Master kill-switch for the ENTIRE email system. When true, _send_email
    # drops every outbound message regardless of EMAIL_MODE or force=True —
    # match intros, mutual-match, engagement, reciprocity cron, operator batch
    # scripts, everything. The ONE exception is account-recovery mail marked
    # critical=True (password reset), so locked-out users can still get back in.
    # This is the real off-switch: EMAIL_MODE=off alone does NOT stop the
    # force-send paths (match digest, reciprocity cron, welcome, meeting
    # confirmation all force-send).
    # Default True (post-event, 2026-06-10): the whole system ships dark so no
    # deploy can email without a deliberate opt-in. To re-enable, set
    # EMAIL_GLOBAL_DISABLED=false on Railway AND ensure EMAIL_MODE / the
    # per-cron flags (MATCH_DIGEST_ENABLED, RECIPROCITY_NOTIFY_ENABLED) are set.
    EMAIL_GLOBAL_DISABLED: bool = True

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

    # Supabase REST / Storage. Service-role key bypasses RLS — server-side
    # only, never expose to the client. Used by the avatar upload service.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Reciprocity-notify kill-switch. Default OFF so the cron is dormant
    # until explicitly enabled via Railway env var. Set to true to activate
    # forward-interest + mutual-completion emails every 2h. EMAIL_MODE alone
    # cannot stop this job because the cron force-sends; this flag is the
    # real off-switch.
    RECIPROCITY_NOTIFY_ENABLED: bool = False

    # Kill-switch for the 09:00 UTC match-digest cron ("N new top matches for
    # Proof of Talk 2026"). Cron is wired in main.py but the body short-
    # circuits when False. Flip true on Railway only after attendees.
    # last_match_digest_at has been bootstrapped to a sensible cutoff (and
    # after any in-flight full-refresh has finished, which would bump every
    # Match.created_at past the stamp and cause a fire-everyone first run).
    MATCH_DIGEST_ENABLED: bool = False

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
