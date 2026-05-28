"""Morning-of email: 'You have N meetings today' sent at 07:00 Europe/Paris
on each conference day (2026-06-02, 2026-06-03).

Only fires on the two conference dates - all other days the cron is a no-op
so leaving the schedule wired up year-round is safe.

`meeting_time` in the Match model is a naive datetime representing Paris
wall-clock (see app/services/slots.py for the canonical comment). Day-boundary
filtering is therefore a simple [day, day+1) range on naive timestamps.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.attendee import Attendee, Match
from app.services.email import send_morning_schedule_email


CONFERENCE_DAYS: tuple[date, date] = (date(2026, 6, 2), date(2026, 6, 3))


def _event_day_label(d: date) -> str:
    return f"Day 1 - June 2" if d == date(2026, 6, 2) else f"Day 2 - June 3"


def _format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


async def _attendee_meetings_for_day(
    db: AsyncSession, day: date
) -> dict[str, list[dict]]:
    """Return {attendee_id_str: [meeting dicts sorted by time]} for the given day.

    Includes only mutually-accepted matches with a meeting_time on `day`.
    """
    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    rows = (
        await db.execute(
            select(Match).where(
                Match.meeting_time.is_not(None),
                Match.meeting_time >= day_start,
                Match.meeting_time < day_end,
                Match.status_a == "accepted",
                Match.status_b == "accepted",
            )
        )
    ).scalars().all()
    if not rows:
        return {}

    attendee_ids: set[str] = set()
    for m in rows:
        attendee_ids.add(str(m.attendee_a_id))
        attendee_ids.add(str(m.attendee_b_id))

    attendees = (
        await db.execute(
            select(Attendee).where(Attendee.id.in_(list(attendee_ids)))
        )
    ).scalars().all()
    by_id = {str(a.id): a for a in attendees}

    out: dict[str, list[dict]] = {aid: [] for aid in attendee_ids}
    for m in rows:
        a_id, b_id = str(m.attendee_a_id), str(m.attendee_b_id)
        other_a = by_id.get(b_id)
        other_b = by_id.get(a_id)
        location = m.meeting_location or "Location TBC - check the app"
        if other_a is not None:
            out[a_id].append({
                "time": _format_time(m.meeting_time),
                "name": other_a.name or "Your match",
                "company": other_a.company or "",
                "location": location,
                "_sort_key": m.meeting_time,
            })
        if other_b is not None:
            out[b_id].append({
                "time": _format_time(m.meeting_time),
                "name": other_b.name or "Your match",
                "company": other_b.company or "",
                "location": location,
                "_sort_key": m.meeting_time,
            })

    for aid in list(out.keys()):
        out[aid].sort(key=lambda x: x["_sort_key"])
        for m in out[aid]:
            m.pop("_sort_key", None)
    return out


async def run_morning_schedule(target_day: date | None = None) -> dict:
    """Iterate all attendees with mutually-accepted meetings on `target_day` and
    send the morning-of email. Returns stats dict for sync_status heartbeat.

    `target_day` defaults to today in Europe/Paris (cron schedules it that way).
    If the day is not a conference day, returns a disabled result and sends
    nothing - keeping the schedule wired year-round is intentional.
    """
    from zoneinfo import ZoneInfo

    if target_day is None:
        target_day = datetime.now(ZoneInfo("Europe/Paris")).date()

    if target_day not in CONFERENCE_DAYS:
        return {"skipped_non_event_day": True, "day": target_day.isoformat(), "sent": 0}

    event_day = _event_day_label(target_day)
    sent = 0
    skipped = 0
    errors = 0

    async with async_session() as db:
        meetings_by_attendee = await _attendee_meetings_for_day(db, target_day)
        if not meetings_by_attendee:
            return {"day": target_day.isoformat(), "sent": 0, "eligible": 0, "errors": 0}

        attendees = (
            await db.execute(
                select(Attendee).where(Attendee.id.in_(list(meetings_by_attendee.keys())))
            )
        ).scalars().all()

        for a in attendees:
            meetings = meetings_by_attendee.get(str(a.id), [])
            if not meetings:
                skipped += 1
                continue
            if getattr(a, "email_opt_out", False):
                skipped += 1
                continue
            if not a.email:
                skipped += 1
                continue
            try:
                ok = send_morning_schedule_email(
                    to_email=a.email,
                    attendee_name=a.name or "",
                    meetings_today=meetings,
                    event_day=event_day,
                    magic_token=a.magic_access_token,
                    force=True,
                )
                if ok:
                    sent += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

    return {
        "day": target_day.isoformat(),
        "event_day": event_day,
        "eligible": len(meetings_by_attendee),
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
    }
