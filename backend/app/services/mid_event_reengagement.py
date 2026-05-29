"""Mid-event re-engagement cron service.

run_mid_event_reengagement():
    "N new attendees just arrived at the Louvre who match you" email fired
    ONCE on 2026-06-02 at 14:00 Europe/Paris. Targets existing attendees
    whose pool gained at least one curated/priority_intro match where the
    counterpart's attendee row was created on or after 2026-06-02 00:00 UTC
    (i.e. day-of registrations / walk-ins / late check-ins).

    Date-bound by the cron registration (CronTrigger year=2026, month=6,
    day=2). No env-flag gate - the date IS the gate.

    Eligibility per recipient: has email, has magic token, not opt-out,
    not @demo.proofoftalk.io, has >=1 qualifying match.

    Featured arrivals respect b2b_only privacy (company name surfaces, not
    real name).
"""
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.attendee import Attendee, Match
from app.services.email import send_mid_event_reengagement_email

logger = logging.getLogger(__name__)

TARGET_DATE: date = date(2026, 6, 2)
ARRIVAL_CUTOFF_UTC: datetime = datetime(2026, 6, 2, 0, 0, tzinfo=timezone.utc)
ELIGIBLE_TIERS = ("curated", "priority_intro")


def _naive(dt: datetime) -> datetime:
    """Same trick as match_digest_cron - Match.created_at and Attendee.created_at
    come back tz-aware (+00:00) from Supabase; strip for naive comparison."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


async def run_mid_event_reengagement(target_date: date | None = None) -> dict:
    """Send the mid-event re-engagement. Returns stats dict for the heartbeat."""
    from zoneinfo import ZoneInfo
    if target_date is None:
        target_date = datetime.now(ZoneInfo("Europe/Paris")).date()

    if target_date != TARGET_DATE:
        return {"skipped_not_mid_event_day": True, "day": target_date.isoformat(), "sent": 0}

    cutoff = _naive(ARRIVAL_CUTOFF_UTC)
    sent = skipped = errors = 0

    async with async_session() as db:
        match_rows = (
            await db.execute(
                select(Match).where(Match.tier.in_(ELIGIBLE_TIERS))
            )
        ).scalars().all()
        if not match_rows:
            return {"day": target_date.isoformat(), "sent": 0, "eligible": 0, "errors": 0}

        all_ids: set = set()
        for m in match_rows:
            all_ids.add(m.attendee_a_id)
            all_ids.add(m.attendee_b_id)
        attendees = (
            await db.execute(
                select(Attendee).where(Attendee.id.in_(list(all_ids)))
            )
        ).scalars().all()
        by_id = {a.id: a for a in attendees}

        # Per recipient, build list of matches whose COUNTERPART arrived today.
        per_recipient: dict = {}
        for m in match_rows:
            for recipient_id, other_id in (
                (m.attendee_a_id, m.attendee_b_id),
                (m.attendee_b_id, m.attendee_a_id),
            ):
                other = by_id.get(other_id)
                if other is None or other.created_at is None:
                    continue
                if _naive(other.created_at) < cutoff:
                    continue
                # Skip if recipient already reviewed this match - the urgency
                # framing assumes the match is fresh-to-them.
                recipient_side = "a" if m.attendee_a_id == recipient_id else "b"
                if recipient_side == "a" and m.status_a != "pending":
                    continue
                if recipient_side == "b" and m.status_b != "pending":
                    continue
                per_recipient.setdefault(recipient_id, []).append((m, other))

        if not per_recipient:
            return {"day": target_date.isoformat(), "sent": 0, "eligible": 0, "errors": 0}

        for attendee_id, pairs in per_recipient.items():
            try:
                attendee = by_id.get(attendee_id)
                if attendee is None:
                    skipped += 1
                    continue
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

                # Skip recipients who themselves arrived today - they're getting
                # the first-time match_intro email path, not a re-engagement.
                if attendee.created_at is not None and _naive(attendee.created_at) >= cutoff:
                    skipped += 1
                    continue

                # Sort qualifying matches by overall_score desc, take top 3.
                pairs.sort(key=lambda p: p[0].overall_score or 0.0, reverse=True)
                top_arrivals: list[dict] = []
                for _m, other in pairs[:3]:
                    if getattr(other, "privacy_mode", "full") == "b2b_only":
                        name = other.company or "Anonymous"
                        title = ""
                    else:
                        name = other.name or ""
                        title = other.title or ""
                    top_arrivals.append({
                        "name": name,
                        "title": title,
                        "company": other.company or "",
                    })

                ok = send_mid_event_reengagement_email(
                    to_email=email_addr,
                    attendee_name=attendee.name or "",
                    new_arrival_count=len(pairs),
                    top_arrivals=top_arrivals,
                    magic_token=attendee.magic_access_token,
                    force=True,
                )
                if ok:
                    sent += 1
                else:
                    errors += 1
            except Exception as exc:
                logger.warning(
                    "mid_event_reengagement: error for attendee %s: %s",
                    attendee_id, exc, exc_info=True,
                )
                errors += 1

    return {
        "day": target_date.isoformat(),
        "eligible": len(per_recipient),
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
    }
