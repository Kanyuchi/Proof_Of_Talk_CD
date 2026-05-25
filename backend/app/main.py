import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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

async def _async_return(value):
    """Trivial async helper — returns a value as a coroutine so it can be used
    as a coro_factory result inside _run_with_heartbeat."""
    return value


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
    # or a broken main-pipeline session can't suppress this. Retry once on
    # a Supabase pooler disconnect (May 13 morning: heartbeat writes were
    # silently lost when the pooler dropped the connection mid-write, so
    # the dashboard showed stale timestamps even though jobs ran).
    log_stats = {k: v for k, v in stats.items() if k != "inserted_ids"}
    import asyncio as _asyncio
    from sqlalchemy.exc import DBAPIError, OperationalError, InterfaceError
    for attempt in (1, 2):
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
            break
        except (DBAPIError, OperationalError, InterfaceError) as exc:
            if attempt == 2:
                logger.error(f"scheduler: {job_name} heartbeat write failed after retry", error=str(exc))
            else:
                logger.warning(f"scheduler: {job_name} heartbeat write pooler-disconnect, retrying", error=str(exc))
                await _asyncio.sleep(1.0)
        except Exception as exc:
            logger.error(f"scheduler: {job_name} heartbeat write failed", error=str(exc))
            break


# ── Daily Extasy sync + enrichment job ────────────────────────────────────────
async def _daily_extasy_sync():
    from app.services.extasy_sync import sync_and_enrich
    await _run_with_heartbeat("daily_extasy_sync", sync_and_enrich)

async def _daily_checkins_sync():
    from app.services.checkins_sync import sync_checkins_to_db
    await _run_with_heartbeat("daily_checkins_sync", sync_checkins_to_db)

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

async def _daily_enrichment_sweep():
    from app.services.enrichment_sweep import daily_enrichment_sweep
    await _run_with_heartbeat("daily_enrichment_sweep", daily_enrichment_sweep)

async def _daily_match_refresh():
    from app.core.database import async_session
    from app.services.matching import refresh_matches_for_new_attendees
    async def _go():
        async with async_session() as db:
            return await refresh_matches_for_new_attendees(db)
    await _run_with_heartbeat("daily_match_refresh", _go)

async def _daily_usage_snapshot():
    from app.core.database import async_session
    from app.services.usage_snapshot import compute_and_upsert_usage_daily
    async def _go():
        async with async_session() as db:
            return await compute_and_upsert_usage_daily(db)
    await _run_with_heartbeat("daily_usage_snapshot", _go)


async def _reciprocity_notify():
    """Every-2h job: forward-notify pending interests + mutual-completion emails.

    Runs run_interest_notifications then run_mutual_notifications in a single
    session. Both are best-effort; the heartbeat captures combined stats.
    Mutual emails are fully decoupled from the request path (inline send was
    removed from update_match_status in this PR).

    Kill-switch: if RECIPROCITY_NOTIFY_ENABLED is False (the default), the
    actual send functions are skipped entirely. The heartbeat still fires so
    the job shows as alive-but-disabled on the dashboard. Flip the Railway env
    var to true when ready to start sending — no redeploy required.
    """
    if not get_settings().RECIPROCITY_NOTIFY_ENABLED:
        await _run_with_heartbeat("reciprocity_notify", lambda: _async_return({"disabled": True}))
        return

    from app.core.database import async_session
    from app.services.interest_cron import run_interest_notifications, run_mutual_notifications

    async def _go():
        async with async_session() as db:
            interest_stats = await run_interest_notifications(db)
            mutual_stats = await run_mutual_notifications(db)
            return {
                "interest_sent":   interest_stats["sent"],
                "interest_skipped": interest_stats["skipped"],
                "interest_errors": interest_stats["errors"],
                "mutual_sent":     mutual_stats["sent"],
                "mutual_skipped":  mutual_stats["skipped"],
                "mutual_errors":   mutual_stats["errors"],
                "errors": interest_stats["errors"] + mutual_stats["errors"],
            }

    await _run_with_heartbeat("reciprocity_notify", _go)


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
scheduler.add_job(_daily_extasy_sync,       CronTrigger(hour=2, minute=0,  timezone="UTC"), **_JOB_DEFAULTS)
# Check-ins sync at 02:05 UTC — right after extasy_sync so the orders feed used
# for the pass-type join reflects the same morning's data. Recovers per-attendee
# claimed-pass people the buyer-keyed orders feed collapses/misses.
scheduler.add_job(_daily_checkins_sync,     CronTrigger(hour=2, minute=5,  timezone="UTC"), **_JOB_DEFAULTS)
scheduler.add_job(_daily_speakers_sync,     CronTrigger(hour=2, minute=15, timezone="UTC"), **_JOB_DEFAULTS)
scheduler.add_job(_daily_grid_audit,        CronTrigger(hour=2, minute=30, timezone="UTC"), **_JOB_DEFAULTS)
# Enrichment sweep at 03:00 UTC: re-scrapes any attendee with missing
# website / Grid / AI summary / embedding data. Skips LinkedIn (manual
# Playwright path). Closes the last automation gap so operators no
# longer need to remember to run enrich_and_embed.py for new arrivals.
scheduler.add_job(_daily_enrichment_sweep,  CronTrigger(hour=3, minute=0,  timezone="UTC"), **_JOB_DEFAULTS)
# Match refresh moved to 03:30 UTC so it runs AFTER the enrichment
# sweep finishes (was 02:45, before enrichment existed in the cron).
scheduler.add_job(_daily_match_refresh,     CronTrigger(hour=3, minute=30, timezone="UTC"), **_JOB_DEFAULTS)
# Usage snapshot at 03:45 UTC — runs AFTER match refresh so it captures a
# full day of login/magic-link activity into usage_daily (one row/day).
scheduler.add_job(_daily_usage_snapshot,    CronTrigger(hour=3, minute=45, timezone="UTC"), **_JOB_DEFAULTS)
# Reciprocity-notify every 2h: forward pending-interest pull-backs +
# mutual-completion emails. IntervalTrigger fires immediately on startup
# then every 2h. mutual_notified_at dedup prevents double-sends.
scheduler.add_job(_reciprocity_notify,      IntervalTrigger(hours=2), **_JOB_DEFAULTS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    logger.info("scheduler: started — extasy 02:00, speakers 02:15, grid audit 02:30, enrichment 03:00, match refresh 03:30, usage snapshot 03:45 (UTC); reciprocity_notify every 2h")
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
    expose_headers=["X-Refresh-Token"],
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


# ── Sliding token refresh ─────────────────────────────────────────────────────
# When an authenticated request comes in with a still-valid JWT that is
# within 2h of expiry, return a fresh token in the X-Refresh-Token
# response header. The frontend axios interceptor swaps it into
# localStorage on the next response. Net effect: active users never see
# a "session expired" mid-conference; idle users still expire after the
# normal 8h TTL.
@app.middleware("http")
async def sliding_token_refresh(request: Request, call_next):
    response = await call_next(request)
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return response
    token = auth.split(None, 1)[1]
    try:
        import time as _time
        from app.core.security import decode_token, create_access_token
        payload = decode_token(token)
        exp = float(payload.get("exp") or 0)
        sub = payload.get("sub")
        # Refresh if less than 2h left and still valid
        remaining = exp - _time.time()
        if sub and 0 < remaining < 7200:
            response.headers["X-Refresh-Token"] = create_access_token({"sub": sub})
            response.headers.setdefault("Access-Control-Expose-Headers", "X-Refresh-Token")
    except Exception:
        pass  # invalid/expired token — let the route's auth deps handle it
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
