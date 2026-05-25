"""Reciprocity-loop cron service.

Two jobs:

run_interest_notifications(db):
    "N people want to meet you" pull-back emails — sent every 2 hours to
    attendees who have at least one incoming pending interest (other side
    accepted, they have not responded). Throttled: skips if
    last_interest_notified_at is within the last 20 hours.

run_mutual_notifications(db):
    "Mutual match confirmed" emails — sent once per newly mutual match.
    Deduped via matches.mutual_notified_at (set after send; never re-sent
    for the same match). This replaces the inline try/except block that
    was previously inside update_match_status in matches.py; the cron
    now owns all mutual-completion emails.

Both functions:
- Use async SQLAlchemy (no Supabase REST).
- Are best-effort per-attendee / per-match (exceptions caught, tallied).
- Commit once at the end of their run.
- Return {"sent": int, "skipped": int, "errors": int} for the heartbeat.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Attendee, Match
from app.services.email import send_interest_notification, send_mutual_match_email

logger = logging.getLogger(__name__)

# How long to throttle between "people want to meet you" emails per attendee.
_INTEREST_THROTTLE_HOURS = 20


async def run_interest_notifications(db: AsyncSession) -> dict:
    """Send 'N people want to meet you' to eligible attendees.

    Returns {"sent", "skipped", "errors"}.
    """
    sent = skipped = errors = 0

    # Step 1: find all matches where one side is accepted and the other pending.
    # These are the "incoming pending" matches that signal unreciprocated interest.
    result = await db.execute(
        select(Match).where(
            # Either a accepted and b is still pending, or vice-versa
            (
                (Match.status_a == "accepted") & (Match.status_b == "pending")
            ) | (
                (Match.status_b == "accepted") & (Match.status_a == "pending")
            )
        )
    )
    matches = result.scalars().all()

    # Step 2: aggregate per-pending-attendee counts.
    counts: dict = {}   # attendee_id (uuid) -> incoming count
    for m in matches:
        if m.status_a == "accepted" and m.status_b == "pending":
            counts[m.attendee_b_id] = counts.get(m.attendee_b_id, 0) + 1
        if m.status_b == "accepted" and m.status_a == "pending":
            counts[m.attendee_a_id] = counts.get(m.attendee_a_id, 0) + 1

    if not counts:
        return {"sent": 0, "skipped": 0, "errors": 0}

    # Step 3: for each attendee with ≥1 incoming, apply eligibility checks.
    throttle_cutoff = datetime.utcnow() - timedelta(hours=_INTEREST_THROTTLE_HOURS)

    for attendee_id, count in counts.items():
        try:
            attendee: Attendee | None = await db.get(Attendee, attendee_id)
            if attendee is None:
                skipped += 1
                continue

            email = (attendee.email or "").strip()
            if not email:
                skipped += 1
                continue
            if getattr(attendee, "email_opt_out", False):
                skipped += 1
                continue
            if email.lower().endswith("@demo.proofoftalk.io"):
                skipped += 1
                continue
            if not attendee.magic_access_token:
                skipped += 1
                continue
            # Throttle: skip if last notified within the last 20 hours
            last_notified = getattr(attendee, "last_interest_notified_at", None)
            if last_notified is not None and last_notified >= throttle_cutoff:
                skipped += 1
                continue

            # Eligible — send
            ok = send_interest_notification(
                to_email=email,
                attendee_name=attendee.name or "",
                count=count,
                magic_token=attendee.magic_access_token,
                force=True,
            )
            if ok:
                attendee.last_interest_notified_at = datetime.utcnow()
                sent += 1
            else:
                skipped += 1

        except Exception as exc:
            logger.warning(
                "interest_cron: error processing attendee %s: %s",
                attendee_id, exc, exc_info=True,
            )
            errors += 1

    # Commit all timestamp stamps in one shot.
    try:
        await db.commit()
    except Exception as exc:
        logger.error("interest_cron: commit failed: %s", exc)

    return {"sent": sent, "skipped": skipped, "errors": errors}


async def run_mutual_notifications(db: AsyncSession) -> dict:
    """Send 'mutual match confirmed' emails for newly mutual matches.

    Finds matches where status='accepted' AND mutual_notified_at IS NULL.
    Sends to both parties (respecting opt-out / no-email per-party).
    Stamps mutual_notified_at=now after sending (dedup guard).

    Returns {"sent", "skipped", "errors"}.
    """
    sent = skipped = errors = 0

    # Fetch all un-notified mutual matches.
    result = await db.execute(
        select(Match).where(
            Match.status == "accepted",
            Match.mutual_notified_at.is_(None),
        )
    )
    matches = result.scalars().all()

    for match in matches:
        try:
            attendee_a: Attendee | None = await db.get(Attendee, match.attendee_a_id)
            attendee_b: Attendee | None = await db.get(Attendee, match.attendee_b_id)

            match_had_send = False

            for recipient, partner in [
                (attendee_a, attendee_b),
                (attendee_b, attendee_a),
            ]:
                if recipient is None:
                    skipped += 1
                    continue
                email = (recipient.email or "").strip()
                if not email:
                    skipped += 1
                    continue
                if getattr(recipient, "email_opt_out", False):
                    skipped += 1
                    continue

                partner_name = partner.name if partner else ""
                partner_title = (partner.title if partner and hasattr(partner, "title") else "") or ""
                partner_company = (partner.company if partner and hasattr(partner, "company") else "") or ""

                ok = send_mutual_match_email(
                    to_email=email,
                    attendee_name=recipient.name or "",
                    other_name=partner_name or "",
                    other_title=partner_title,
                    other_company=partner_company,
                    magic_token=getattr(recipient, "magic_access_token", None),
                    force=True,
                )
                if ok:
                    sent += 1
                    match_had_send = True
                else:
                    skipped += 1

            # Stamp the match regardless of per-party opt-outs (prevents
            # re-processing this match forever when one side has no email).
            match.mutual_notified_at = datetime.utcnow()

        except Exception as exc:
            logger.warning(
                "interest_cron: error processing match %s: %s",
                match.id, exc, exc_info=True,
            )
            errors += 1

    try:
        await db.commit()
    except Exception as exc:
        logger.error("interest_cron: mutual commit failed: %s", exc)

    return {"sent": sent, "skipped": skipped, "errors": errors}
