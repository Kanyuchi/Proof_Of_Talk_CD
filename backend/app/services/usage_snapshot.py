# backend/app/services/usage_snapshot.py
"""Daily usage snapshot — writes one usage_daily row per UTC day.

"last_active" for a person = max(users.last_login_at, attendees.last_seen_at)
for their linked rows. A person who both logged in and opened a magic link is
counted once (we de-dupe on the attendee link).

active_today / cumulative_active count only people who have an *account*
(a non-admin, non-demo `users` row). Magic-link openers who never created an
account are visible separately on the dashboard via `magic_link_active` (which
still counts every opener for engagement reporting); they are excluded here so
that `cumulative_active <= real_accounts` by construction.

See docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.attendee import Attendee

logger = logging.getLogger(__name__)

_DEMO_SUFFIX = "@demo.proofoftalk.io"


def _active_user_filter():
    """WHERE clauses dropping admin + demo accounts from 'active' user counts.

    Mirrors the `real_accounts` predicate so active metrics can't be inflated
    by operator/admin logins or the 7 seeded demo personas. Returned as a tuple
    so callers splat it into `.where(..., *_active_user_filter())`.
    """
    return (
        User.is_admin.is_(False),
        ~func.lower(func.coalesce(User.email, "")).like(f"%{_DEMO_SUFFIX}"),
    )


def _active_attendee_filter():
    """WHERE clauses dropping demo + admin-linked attendees from magic-link
    'active' counts. Demo personas are matched by email suffix; an admin's own
    attendee row is matched via the same admin subquery pattern used in
    dashboard `/stats`.

    NOTE: this filter does NOT require the attendee to have a user account, so
    it remains usable for the "Magic-link opens" engagement stat that includes
    unregistered openers. For "active accounts" metrics, splat
    `_account_linked_filter()` as well.
    """
    admin_attendee_subq = (
        select(User.attendee_id)
        .where(User.is_admin.is_(True), User.attendee_id.isnot(None))
        .scalar_subquery()
    )
    return (
        ~func.lower(func.coalesce(Attendee.email, "")).like(f"%{_DEMO_SUFFIX}"),
        ~Attendee.id.in_(admin_attendee_subq),
    )


def _account_linked_filter():
    """WHERE clause requiring the attendee row to be linked to a real (non-admin,
    non-demo) user account. Used alongside `_active_attendee_filter()` for the
    "active accounts" metrics so a magic-link open from a directory row that
    never registered does not inflate the active count above total accounts.
    """
    has_real_user = (
        select(User.id)
        .where(
            User.attendee_id == Attendee.id,
            User.is_admin.is_(False),
            ~func.lower(func.coalesce(User.email, "")).like(f"%{_DEMO_SUFFIX}"),
        )
        .exists()
    )
    return (has_real_user,)


async def compute_and_upsert_usage_daily(db: AsyncSession) -> dict:
    """Compute today's usage_daily row and upsert it (idempotent on `day`).
    Returns a stats dict for the cron heartbeat."""
    now = datetime.utcnow()
    today = now.date()
    cutoff = now - timedelta(hours=24)

    total_accounts = (await db.execute(select(func.count(User.id)))).scalar() or 0
    real_accounts = (
        await db.execute(
            select(func.count(User.id)).where(
                User.is_admin.is_(False),
                ~func.lower(User.email).like(f"%{_DEMO_SUFFIX}"),
            )
        )
    ).scalar() or 0

    # Ever-active users: (attendee_id, last_login_at). attendee_id may be None.
    # Admin + demo accounts excluded so they never inflate active metrics.
    user_rows = (
        await db.execute(
            select(User.attendee_id, User.last_login_at).where(
                User.last_login_at.isnot(None),
                *_active_user_filter(),
            )
        )
    ).all()
    # Ever-active attendees with an account: (id, last_seen_at). Demo +
    # admin-linked + no-account openers excluded so cumulative_active stays
    # bounded by real_accounts.
    att_rows = (
        await db.execute(
            select(Attendee.id, Attendee.last_seen_at).where(
                Attendee.last_seen_at.isnot(None),
                *_active_attendee_filter(),
                *_account_linked_filter(),
            )
        )
    ).all()

    # De-dupe a person who appears as both a logged-in user and a seen
    # attendee, via the user's attendee_id link.
    login_attendee_ids = {r[0] for r in user_rows if r[0] is not None}

    cumulative_active = len(user_rows) + sum(
        1 for (aid, _seen) in att_rows if aid not in login_attendee_ids
    )

    active_user_count = sum(1 for (_aid, ts) in user_rows if ts and ts >= cutoff)
    login_attendee_ids_24h = {
        r[0] for r in user_rows if r[0] is not None and r[1] and r[1] >= cutoff
    }
    active_magic_count = sum(
        1 for (aid, seen) in att_rows
        if seen and seen >= cutoff and aid not in login_attendee_ids_24h
    )
    active_today = active_user_count + active_magic_count

    await db.execute(
        text("""
            INSERT INTO usage_daily
                (day, total_accounts, real_accounts, active_today, cumulative_active)
            VALUES
                (:day, :total_accounts, :real_accounts, :active_today, :cumulative_active)
            ON CONFLICT (day) DO UPDATE SET
                total_accounts    = EXCLUDED.total_accounts,
                real_accounts     = EXCLUDED.real_accounts,
                active_today      = EXCLUDED.active_today,
                cumulative_active = EXCLUDED.cumulative_active
        """),
        {
            "day": today,
            "total_accounts": total_accounts,
            "real_accounts": real_accounts,
            "active_today": active_today,
            "cumulative_active": cumulative_active,
        },
    )
    await db.commit()

    stats = {
        "day": today.isoformat(),
        "total_accounts": total_accounts,
        "real_accounts": real_accounts,
        "active_today": active_today,
        "cumulative_active": cumulative_active,
    }
    logger.info("usage_snapshot: %s", stats)
    return stats
