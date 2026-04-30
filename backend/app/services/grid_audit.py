"""
Grid coverage audit — service layer
====================================
Daily-scheduled equivalent of `scripts/grid_domain_audit.py`. Reuses the
URL-search and slug-search primitives from `grid_enrichment.py` so the
matching policy is consistent with what live enrichment would produce.

Persists one row per run into `grid_audit_runs` for trend tracking, and
exposes the previous run via `last_audit()` so the admin dashboard can
surface deltas without re-running the audit.

Why a separate service from `scripts/grid_domain_audit.py`:
- The script is operator-facing (CSV output, stdout progress, Supabase REST).
- This service is app-facing (returns a structured summary, persists via
  SQLAlchemy, runs inside the FastAPI lifespan).

Both paths use the same Grid GraphQL primitives so coverage numbers agree.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import select, desc

# Load .env so the service works whether invoked via uvicorn (env already
# present), the APScheduler hook (env already present), or a one-off
# `python -m`/`python -c` command line (which won't have loaded .env yet).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.core.database import async_session
from app.models.attendee import Attendee
from app.models.grid_audit_run import GridAuditRun
from app.services.grid_enrichment import (
    GRID_GRAPHQL_URL,
    URL_SEARCH_QUERY,
    _PLATFORM_DOMAINS,
)

logger = logging.getLogger(__name__)

# Personal-email domains where a "company" Grid lookup is meaningless.
# Mirrors GENERIC_DOMAINS in scripts/grid_domain_audit.py.
GENERIC_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "googlemail.com", "protonmail.com", "proton.me", "pm.me", "me.com",
    "live.com", "aol.com", "msn.com",
})

GRID_API_DELAY_SECONDS = 0.5  # be polite to thegrid.id


async def _fetch_attendee_domains() -> list[dict]:
    """Group attendee emails by domain. Returns
    [{'domain': 'x.com', 'attendee_count': N, 'has_grid': bool}].

    Uses the SQLAlchemy session (DATABASE_URL) rather than Supabase REST so
    we don't depend on SUPABASE_SERVICE_ROLE_KEY staying in sync with key
    rotations on Railway.
    """
    async with async_session() as session:
        result = await session.execute(select(Attendee.email, Attendee.enriched_profile))
        rows = result.all()

    buckets: dict[str, dict] = {}
    for email, enriched_profile in rows:
        email = (email or "").lower()
        if "@" not in email:
            continue
        domain = email.split("@")[1]
        if domain in GENERIC_DOMAINS:
            continue
        ep = enriched_profile or {}
        has_grid = bool(ep.get("grid"))
        bucket = buckets.setdefault(domain, {"domain": domain, "attendee_count": 0, "has_grid": False})
        bucket["attendee_count"] += 1
        if has_grid:
            bucket["has_grid"] = True
    return sorted(buckets.values(), key=lambda x: x["domain"])


async def _grid_url_search(client: httpx.AsyncClient, domain: str) -> dict | None:
    """Return the first Grid profile whose URL list contains the given domain,
    or None. Mirrors the strategy-1 path in grid_enrichment.enrich_from_grid.
    """
    if domain.lower() in _PLATFORM_DOMAINS:
        return None
    for variant in (domain, domain.lower()):
        try:
            resp = await client.post(
                GRID_GRAPHQL_URL,
                json={"query": URL_SEARCH_QUERY, "variables": {"pattern": f"%{variant}%"}},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                continue
            for profile in (data.get("data") or {}).get("profileInfos") or []:
                for u in (profile.get("urls") or []):
                    if domain.lower() in (u.get("url") or "").lower():
                        return profile
        except Exception:
            continue
    return None


async def run_grid_audit() -> dict:
    """Run the audit and return a structured summary. No persistence — caller
    decides what to do with the result.

    Result shape:
        {
          "run_at": ISO datetime,
          "duration_seconds": float,
          "total_domains": int,
          "total_attendees": int,
          "matched_domains": int,
          "matched_attendees": int,
          "had_grid_before_count": int,
          "new_matches":      [{"domain", "grid_slug", "grid_name", "sector"}],
          "unmatched_domains": ["domain.com", ...],
          "rows": [...full per-domain rows...],
        }
    """
    started = time.monotonic()
    run_at = datetime.now(timezone.utc)

    domains = await _fetch_attendee_domains()
    rows: list[dict] = []
    new_matches: list[dict] = []
    unmatched: list[str] = []

    async with httpx.AsyncClient(timeout=20) as client:
        for d in domains:
            domain = d["domain"]
            profile = await _grid_url_search(client, domain)
            if profile:
                name = profile.get("name") or ""
                slug = name.lower().replace(" ", "_")
                sector = (profile.get("profileSector") or {}).get("name", "")
                rows.append({
                    **d,
                    "grid_slug": slug,
                    "grid_name": name,
                    "grid_sector": sector,
                })
                # "New" = Grid has it, but no attendee on this domain has it
                # attached yet. These are the rows that should be backfilled.
                if not d["has_grid"]:
                    new_matches.append({
                        "domain": domain,
                        "grid_slug": slug,
                        "grid_name": name,
                        "sector": sector,
                    })
            else:
                rows.append({**d, "grid_slug": None, "grid_name": None, "grid_sector": None})
                unmatched.append(domain)

            import asyncio
            await asyncio.sleep(GRID_API_DELAY_SECONDS)

    matched_domains = sum(1 for r in rows if r.get("grid_slug"))
    matched_attendees = sum(r["attendee_count"] for r in rows if r.get("grid_slug"))
    total_attendees = sum(r["attendee_count"] for r in rows)
    had_grid_before = sum(1 for r in rows if r.get("has_grid"))

    return {
        "run_at": run_at.isoformat(),
        "duration_seconds": round(time.monotonic() - started, 2),
        "total_domains": len(rows),
        "total_attendees": total_attendees,
        "matched_domains": matched_domains,
        "matched_attendees": matched_attendees,
        "had_grid_before_count": had_grid_before,
        "new_matches": new_matches,
        "unmatched_domains": unmatched,
        "rows": rows,
    }


async def persist_audit_run(summary: dict) -> str:
    """Write a row to grid_audit_runs and return the new row id."""
    async with async_session() as session:
        row = GridAuditRun(
            run_at=datetime.fromisoformat(summary["run_at"]).replace(tzinfo=None),
            total_domains=summary["total_domains"],
            total_attendees=summary["total_attendees"],
            matched_domains=summary["matched_domains"],
            matched_attendees=summary["matched_attendees"],
            had_grid_before_count=summary["had_grid_before_count"],
            new_matches=summary["new_matches"],
            unmatched_domains=summary["unmatched_domains"],
            duration_seconds=summary.get("duration_seconds"),
        )
        session.add(row)
        await session.commit()
        return str(row.id)


async def last_audit() -> dict | None:
    """Fetch the most recent audit row. Used by the admin dashboard."""
    async with async_session() as session:
        result = await session.execute(
            select(GridAuditRun).order_by(desc(GridAuditRun.run_at)).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return {
            "id": str(row.id),
            "run_at": row.run_at.isoformat(),
            "total_domains": row.total_domains,
            "total_attendees": row.total_attendees,
            "matched_domains": row.matched_domains,
            "matched_attendees": row.matched_attendees,
            "had_grid_before_count": row.had_grid_before_count,
            "new_matches": row.new_matches or [],
            "unmatched_domains": row.unmatched_domains or [],
            "duration_seconds": row.duration_seconds,
        }


async def run_and_persist() -> dict:
    """Convenience wrapper for the scheduler. Runs the audit, persists the
    summary, and returns the persisted summary (without the heavy `rows`
    field). Errors are logged and re-raised so the scheduler can record
    them; we never silently swallow them.
    """
    started = time.monotonic()
    try:
        summary = await run_grid_audit()
        row_id = await persist_audit_run(summary)
        logger.info(
            "grid_audit: complete id=%s domains=%d/%d attendees=%d/%d new_matches=%d duration=%ss",
            row_id,
            summary["matched_domains"], summary["total_domains"],
            summary["matched_attendees"], summary["total_attendees"],
            len(summary["new_matches"]),
            summary["duration_seconds"],
        )
        summary.pop("rows", None)
        summary["id"] = row_id
        return summary
    except Exception as exc:
        # Persist the failure so dashboard surfaces "audit broken" clearly.
        async with async_session() as session:
            row = GridAuditRun(
                total_domains=0,
                total_attendees=0,
                matched_domains=0,
                matched_attendees=0,
                duration_seconds=round(time.monotonic() - started, 2),
                error=f"{type(exc).__name__}: {exc}",
            )
            session.add(row)
            await session.commit()
        logger.error("grid_audit: failed: %s", exc)
        raise
