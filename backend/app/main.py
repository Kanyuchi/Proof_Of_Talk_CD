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

# ── Scheduler heartbeat wrapper ───────────────────────────────────────────────
# Every cron job runs through _run_with_heartbeat so that the sync_status
# table always records last_run_at + status + stats — even if the job
# raises an unhandled exception. This is what makes silent-drift failures
# (May 5-6 incident) impossible to miss: the dashboard surfaces stale
# timestamps the next morning instead of us having to dig through Railway
# logs after the fact.
async def _run_with_heartbeat(job_name: str, coro_factory):
    """Run a cron job and unconditionally write a sync_status heartbeat.

    `coro_factory` is a zero-arg callable returning a fresh coroutine each
    call (so we can re-await on retry without RuntimeError). Returns the
    job's result dict on success, None on failure.
    """
    import json as _json
    from sqlalchemy import text as _text
    from app.core.database import async_session

    status = "ok"
    stats: dict = {}
    error_msg: str | None = None
    try:
        result = await coro_factory()
        stats = result if isinstance(result, dict) else {"result": str(result)}
        if stats.get("errors", 0) > 0 or stats.get("chunks_failed", 0) > 0:
            status = "partial"
        logger.info(f"scheduler: {job_name} complete", status=status, **{k: v for k, v in stats.items() if k != "inserted_ids"})
    except Exception as exc:
        status = "error"
        error_msg = f"{type(exc).__name__}: {exc}"
        stats = {"error": error_msg}
        logger.error(f"scheduler: {job_name} failed", error=error_msg)

    # Heartbeat write in its own session — a poisoned scheduler event loop
    # or a broken main-pipeline session can't suppress this.
    log_stats = {k: v for k, v in stats.items() if k != "inserted_ids"}
    try:
        async with async_session() as db:
            await db.execute(
                _text("""
                    INSERT INTO sync_status (job_name, last_run_at, last_status, stats)
                    VALUES (:job, NOW(), :status, CAST(:stats AS JSONB))
                    ON CONFLICT (job_name) DO UPDATE SET
                        last_run_at = NOW(),
                        last_status = EXCLUDED.last_status,
                        stats = EXCLUDED.stats
                """),
                {"job": job_name, "status": status, "stats": _json.dumps(log_stats)},
            )
            await db.commit()
    except Exception as exc:
        logger.error(f"scheduler: {job_name} heartbeat write failed", error=str(exc))


# ── Daily Extasy sync + enrichment job ────────────────────────────────────────
async def _daily_extasy_sync():
    from app.services.extasy_sync import sync_and_enrich
    await _run_with_heartbeat("daily_extasy_sync", sync_and_enrich)

async def _daily_speakers_sync():
    from app.services.speakers_sheet_sync import sync_speakers_sheet
    await _run_with_heartbeat("daily_speakers_sync", lambda: sync_speakers_sheet(fetch=True))

async def _daily_grid_audit():
    from app.services.grid_audit import run_and_persist
    async def _go():
        summary = await run_and_persist()
        return {
            "matched_domains":   summary["matched_domains"],
            "total_domains":     summary["total_domains"],
            "matched_attendees": summary["matched_attendees"],
            "total_attendees":   summary["total_attendees"],
            "new_matches":       len(summary["new_matches"]),
        }
    await _run_with_heartbeat("daily_grid_audit", _go)

async def _daily_match_refresh():
    from app.core.database import async_session
    from app.services.matching import refresh_matches_for_new_attendees
    async def _go():
        async with async_session() as db:
            return await refresh_matches_for_new_attendees(db)
    await _run_with_heartbeat("daily_match_refresh", _go)

# coalesce + max_instances + misfire_grace_time are the APScheduler-level
# protections that catch the OTHER half of the May 5-6 failure: container
# restarts that miss the cron window, or jobs that stack up after a bad
# night. coalesce=True collapses missed runs into one, max_instances=1
# blocks overlapping runs, misfire_grace_time gives a 15-min window for
# Railway to come back online before the run is dropped.
_JOB_DEFAULTS = {
    "coalesce":           True,
    "max_instances":      1,
    "misfire_grace_time": 900,
}

scheduler = AsyncIOScheduler()
scheduler.add_job(_daily_extasy_sync,   CronTrigger(hour=2, minute=0,  timezone="UTC"), **_JOB_DEFAULTS)
scheduler.add_job(_daily_speakers_sync, CronTrigger(hour=2, minute=15, timezone="UTC"), **_JOB_DEFAULTS)
scheduler.add_job(_daily_grid_audit,    CronTrigger(hour=2, minute=30, timezone="UTC"), **_JOB_DEFAULTS)
scheduler.add_job(_daily_match_refresh, CronTrigger(hour=2, minute=45, timezone="UTC"), **_JOB_DEFAULTS)

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
