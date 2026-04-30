import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.limiter import limiter
from app.api.routes import attendees, matches, enrichment, dashboard, auth, chat, messages, threads, integration

settings = get_settings()

# ── Structured logging ────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logger = structlog.get_logger(__name__)

# ── Daily Extasy sync + enrichment job ────────────────────────────────────────
async def _daily_extasy_sync():
    try:
        from app.services.extasy_sync import sync_and_enrich
        result = await sync_and_enrich()
        logger.info("scheduler: daily extasy sync complete", **result)
    except Exception as exc:
        logger.error("scheduler: daily extasy sync failed", error=str(exc))

async def _daily_speakers_sync():
    try:
        from app.services.speakers_sync import sync_and_enrich
        result = await sync_and_enrich()
        logger.info("scheduler: daily speakers sync complete", **result)
    except Exception as exc:
        logger.error("scheduler: daily speakers sync failed", error=str(exc))

async def _daily_grid_audit():
    try:
        from app.services.grid_audit import run_and_persist
        summary = await run_and_persist()
        logger.info("scheduler: daily grid audit complete",
                    matched_domains=summary["matched_domains"],
                    total_domains=summary["total_domains"],
                    matched_attendees=summary["matched_attendees"],
                    total_attendees=summary["total_attendees"],
                    new_matches=len(summary["new_matches"]))
    except Exception as exc:
        logger.error("scheduler: daily grid audit failed", error=str(exc))

async def _daily_match_refresh():
    try:
        from app.core.database import async_session
        from app.services.matching import refresh_matches_for_new_attendees
        async with async_session() as db:
            result = await refresh_matches_for_new_attendees(db)
        logger.info("scheduler: daily match refresh complete", **result)
    except Exception as exc:
        logger.error("scheduler: daily match refresh failed", error=str(exc))

scheduler = AsyncIOScheduler()
# Run every day at 02:00 UTC — after midnight registrations settle
scheduler.add_job(_daily_extasy_sync, CronTrigger(hour=2, minute=0, timezone="UTC"))
# Speakers sync at 02:15 UTC — after Extasy sync completes
scheduler.add_job(_daily_speakers_sync, CronTrigger(hour=2, minute=15, timezone="UTC"))
# Grid coverage audit at 02:30 UTC — after both sync jobs settle
scheduler.add_job(_daily_grid_audit, CronTrigger(hour=2, minute=30, timezone="UTC"))
# Match refresh at 02:45 UTC — fills in matches for new attendees from
# Extasy/speakers syncs without disturbing existing accept/decline state
scheduler.add_job(_daily_match_refresh, CronTrigger(hour=2, minute=45, timezone="UTC"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    logger.info("scheduler: started — extasy 02:00, speakers 02:15, grid audit 02:30, match refresh 02:45 (UTC)")
    yield
    scheduler.shutdown(wait=False)
    logger.info("scheduler: stopped")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Matchmaking Engine for Proof of Talk 2026",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# ── Security headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# ── Global exception handler (no stack traces in responses) ──────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=str(request.url), method=request.method, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred."},
    )

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(attendees.router, prefix=settings.API_V1_PREFIX)
app.include_router(matches.router, prefix=settings.API_V1_PREFIX)
app.include_router(enrichment.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(messages.router, prefix=settings.API_V1_PREFIX)
app.include_router(threads.router, prefix=settings.API_V1_PREFIX)
app.include_router(integration.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
