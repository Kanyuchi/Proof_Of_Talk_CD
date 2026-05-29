"""Match-digest cron service.

run_match_digest(db):
    "N new top matches" digest email — sent daily (09:00 UTC cron) to
    existing attendees whose curated pool gained >= threshold new matches
    since the last digest. Per-attendee 72h throttle via
    attendees.last_match_digest_at. Highest-overall-score match is
    featured in the email body.

    A "new" match for attendee A is a Match row where:
      - A is on one side (attendee_a_id or attendee_b_id)
      - tier in ('curated', 'priority_intro')
      - created_at > A.last_match_digest_at (or all matches if NULL)
      - A's per-side status is still 'pending' (un-reviewed)

This complements send_match_intro_email (which fires once on first
match-generation) by keeping existing attendees informed when fresh
top-tier candidates land in their pool.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Attendee, Match
from app.services.email import send_match_digest_email

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 3
DEFAULT_THROTTLE_HOURS = 72
# Per-run safety cap. Stops a runaway from cooking sender reputation if a
# scenario (mass new-attendee insert, cold-start without bootstrap) produces
# more eligible recipients than the warm domain can absorb in one fire.
# Steady-state daily eligible count is ~50-100; this is the panic-stop.
DEFAULT_MAX_SENDS = 200
DIGEST_TIERS = ("curated", "priority_intro")


def _naive(dt: datetime) -> datetime:
    """Strip tzinfo so naive cutoffs compare cleanly. Match.created_at comes
    back from Postgres as tz-aware (+00:00) even though the model declares
    DateTime without timezone=True; the codebase's other crons use naive
    datetime.utcnow(), so we normalize the DB side."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


async def run_match_digest(
    db: AsyncSession,
    threshold: int = DEFAULT_THRESHOLD,
    throttle_hours: int = DEFAULT_THROTTLE_HOURS,
    max_sends: int = DEFAULT_MAX_SENDS,
    now: datetime | None = None,
) -> dict:
    """Send the new-matches digest. Returns {sent, skipped, errors, eligible}.

    `max_sends` caps a single run to protect sender reputation. When the cap
    bites, the cron exits early; the remainder are picked up the next day.
    """
    if now is None:
        now = datetime.utcnow()
    sent = skipped = errors = 0

    # Step 1: pull every curated/priority_intro match in scope. Filter
    # in-memory so we can apply per-attendee created_at-vs-last_digest_at
    # logic without a self-join.
    result = await db.execute(
        select(Match).where(Match.tier.in_(DIGEST_TIERS))
    )
    all_matches = result.scalars().all()

    # Step 2: aggregate per-attendee. For each attendee, collect matches
    # where THEIR side is still pending (un-reviewed).
    per_attendee: dict = {}   # attendee_id -> list[Match]
    for m in all_matches:
        # Side A's pool: A is recipient; A's pending status counts the row.
        if m.status_a == "pending":
            per_attendee.setdefault(m.attendee_a_id, []).append((m, "a"))
        # Side B's pool: B is recipient; B's pending status counts the row.
        if m.status_b == "pending":
            per_attendee.setdefault(m.attendee_b_id, []).append((m, "b"))

    if not per_attendee:
        return {"sent": 0, "skipped": 0, "errors": 0, "eligible": 0}

    eligible_count = 0
    throttle_cutoff = now - timedelta(hours=throttle_hours)

    # Step 3: for each candidate, fetch attendee, filter to *new* matches,
    # check eligibility, send.
    for attendee_id, match_tuples in per_attendee.items():
        try:
            attendee: Attendee | None = await db.get(Attendee, attendee_id)
            if attendee is None:
                skipped += 1
                continue

            # Throttle: skip if last digest was within the throttle window.
            last_digest = attendee.last_match_digest_at
            if last_digest is not None and _naive(last_digest) >= throttle_cutoff:
                skipped += 1
                continue

            # "New since last digest" — if never sent, every pending match counts.
            cutoff = _naive(last_digest) if last_digest is not None else datetime.min
            new_matches = [m for m, _side in match_tuples if _naive(m.created_at) > cutoff]
            if len(new_matches) < threshold:
                skipped += 1
                continue

            eligible_count += 1

            # Standard send-gates (mirrors interest_cron).
            email_addr = (attendee.email or "").strip()
            if not email_addr:
                skipped += 1
                continue
            if getattr(attendee, "email_opt_out", False):
                skipped += 1
                continue
            if email_addr.lower().endswith("@demo.proofoftalk.io"):
                skipped += 1
                continue
            if not attendee.magic_access_token:
                skipped += 1
                continue

            # Feature the highest-overall-score new match.
            top_match = max(new_matches, key=lambda m: m.overall_score or 0.0)
            top_other_id = (
                top_match.attendee_b_id
                if top_match.attendee_a_id == attendee.id
                else top_match.attendee_a_id
            )
            top_other = await db.get(Attendee, top_other_id)
            if top_other is None:
                skipped += 1
                continue

            # Respect b2b_only privacy on the featured candidate.
            if getattr(top_other, "privacy_mode", "full") == "b2b_only":
                top_name = top_other.company or "Anonymous"
                top_title = ""
            else:
                top_name = top_other.name or ""
                top_title = top_other.title or ""

            ok = send_match_digest_email(
                to_email=email_addr,
                attendee_name=attendee.name or "",
                new_count=len(new_matches),
                top_match_name=top_name,
                top_match_title=top_title,
                top_match_company=top_other.company or "",
                top_explanation=top_match.explanation or "",
                magic_token=attendee.magic_access_token,
                force=True,
            )
            if ok:
                attendee.last_match_digest_at = now
                sent += 1
                if sent >= max_sends:
                    break
            else:
                skipped += 1

        except Exception as exc:
            logger.warning(
                "match_digest_cron: error processing attendee %s: %s",
                attendee_id, exc, exc_info=True,
            )
            errors += 1

    try:
        await db.commit()
    except Exception as exc:
        logger.error("match_digest_cron: commit failed: %s", exc)

    return {
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
        "eligible": eligible_count,
    }
