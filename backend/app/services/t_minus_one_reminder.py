"""T-1 reminder cron service.

run_t_minus_one_reminder():
    "Tomorrow at the Louvre" email fired ONCE on 2026-06-01 at 17:00 Europe/
    Paris. Renders the attendee's top 3 curated/priority_intro matches plus
    a count of meetings already booked, with a CTA back to /matches.

    Date-bound by the cron registration (CronTrigger year=2026, month=6,
    day=1) so the trigger is structurally inert outside that window.
    No env-flag gate - the date IS the gate.

    Eligibility per attendee:
      - has email
      - has magic token
      - not email_opt_out
      - has >=1 curated|priority_intro Match row (skip ticket-only ghosts)
      - not @demo.proofoftalk.io
"""
import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.attendee import Attendee, Match
from app.services.email import send_t_minus_one_reminder_email

logger = logging.getLogger(__name__)

TARGET_DATE: date = date(2026, 6, 1)
ELIGIBLE_TIERS = ("curated", "priority_intro")


def _build_top_matches(
    attendee_id, matches_by_attendee: dict, attendees_by_id: dict
) -> list[dict]:
    """Sort the attendee's pool by overall_score desc, return top-3 as dicts."""
    rows = matches_by_attendee.get(attendee_id, [])
    rows.sort(key=lambda m: m.overall_score or 0.0, reverse=True)
    out: list[dict] = []
    for m in rows[:3]:
        other_id = m.attendee_b_id if m.attendee_a_id == attendee_id else m.attendee_a_id
        other = attendees_by_id.get(other_id)
        if other is None:
            continue
        if getattr(other, "privacy_mode", "full") == "b2b_only":
            name = other.company or "Anonymous"
            title = ""
        else:
            name = other.name or ""
            title = other.title or ""
        out.append({
            "name": name,
            "title": title,
            "company": other.company or "",
        })
    return out


async def run_t_minus_one_reminder(
    target_date: date | None = None,
) -> dict:
    """Send the T-1 reminder. Returns stats dict for sync_status heartbeat.

    `target_date` defaults to today in Europe/Paris. If today isn't the
    bound TARGET_DATE we no-op (defensive — primary gate is the cron itself).
    """
    from zoneinfo import ZoneInfo
    if target_date is None:
        target_date = datetime.now(ZoneInfo("Europe/Paris")).date()

    if target_date != TARGET_DATE:
        return {"skipped_not_t_minus_one_day": True, "day": target_date.isoformat(), "sent": 0}

    sent = skipped = errors = 0

    async with async_session() as db:
        # Step 1: pull every curated/priority_intro match, group by attendee.
        match_rows = (
            await db.execute(
                select(Match).where(Match.tier.in_(ELIGIBLE_TIERS))
            )
        ).scalars().all()

        per_attendee: dict = {}
        all_attendee_ids: set = set()
        for m in match_rows:
            per_attendee.setdefault(m.attendee_a_id, []).append(m)
            per_attendee.setdefault(m.attendee_b_id, []).append(m)
            all_attendee_ids.add(m.attendee_a_id)
            all_attendee_ids.add(m.attendee_b_id)

        if not per_attendee:
            return {"day": target_date.isoformat(), "sent": 0, "eligible": 0, "errors": 0}

        # Step 2: bulk-fetch attendees in one go.
        attendees = (
            await db.execute(
                select(Attendee).where(Attendee.id.in_(list(all_attendee_ids)))
            )
        ).scalars().all()
        by_id = {a.id: a for a in attendees}

        # Step 3: count scheduled mutual meetings per attendee (one pass).
        mutual_rows = (
            await db.execute(
                select(Match).where(
                    Match.status_a == "accepted",
                    Match.status_b == "accepted",
                    Match.meeting_time.is_not(None),
                )
            )
        ).scalars().all()
        scheduled_by_attendee: dict = {}
        for m in mutual_rows:
            scheduled_by_attendee[m.attendee_a_id] = scheduled_by_attendee.get(m.attendee_a_id, 0) + 1
            scheduled_by_attendee[m.attendee_b_id] = scheduled_by_attendee.get(m.attendee_b_id, 0) + 1

        # Step 4: per recipient, check eligibility, build top-3, send.
        for attendee_id, rows in per_attendee.items():
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

                top_matches = _build_top_matches(attendee_id, per_attendee, by_id)
                if not top_matches:
                    skipped += 1
                    continue

                ok = send_t_minus_one_reminder_email(
                    to_email=email_addr,
                    attendee_name=attendee.name or "",
                    top_matches=top_matches,
                    scheduled_count=scheduled_by_attendee.get(attendee_id, 0),
                    total_matches=len(rows),
                    magic_token=attendee.magic_access_token,
                    force=True,
                )
                if ok:
                    sent += 1
                else:
                    errors += 1
            except Exception as exc:
                logger.warning(
                    "t_minus_one_reminder: error for attendee %s: %s",
                    attendee_id, exc, exc_info=True,
                )
                errors += 1

    return {
        "day": target_date.isoformat(),
        "eligible": len(per_attendee),
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
    }
