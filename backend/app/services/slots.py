"""Conference time slots + availability helpers for free-slot visibility on match cards.

The slot grid is the canonical source of bookable times. The frontend mirrors the
same list in `frontend/src/utils/matchHelpers.tsx::CONFERENCE_SLOTS`. Keep both in sync.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Match


# Each slot is a 30-min block at the Louvre Palace, Paris (Europe/Paris).
# Stored as naive UTC for simplicity (matches existing meeting_time semantics).
# Times below are in local Paris wall-clock; matched against meeting_time stored
# the same way (the existing `slotToISO` helper builds naive ISO strings, e.g.
# "2026-06-02T09:00:00", which Postgres reads as naive timestamp).
_RAW_SLOTS: list[tuple[str, str]] = [
    # Day, HH:MM
    ("2026-06-02", "09:00"), ("2026-06-02", "09:30"),
    ("2026-06-02", "10:00"), ("2026-06-02", "10:30"),
    ("2026-06-02", "11:00"), ("2026-06-02", "11:30"),
    ("2026-06-02", "14:00"), ("2026-06-02", "14:30"),
    ("2026-06-02", "15:00"), ("2026-06-02", "15:30"),
    ("2026-06-02", "16:00"), ("2026-06-02", "16:30"),
    ("2026-06-02", "18:00"), ("2026-06-02", "18:30"),
    ("2026-06-02", "19:00"),
    ("2026-06-03", "09:00"), ("2026-06-03", "09:30"),
    ("2026-06-03", "10:00"), ("2026-06-03", "10:30"),
    ("2026-06-03", "11:00"), ("2026-06-03", "11:30"),
    ("2026-06-03", "14:00"), ("2026-06-03", "14:30"),
    ("2026-06-03", "15:00"), ("2026-06-03", "15:30"),
    ("2026-06-03", "16:00"), ("2026-06-03", "16:30"),
]


def all_slots() -> list[datetime]:
    """All bookable conference slots as naive datetimes (Paris wall-clock)."""
    return [datetime.fromisoformat(f"{d}T{t}:00") for d, t in _RAW_SLOTS]


def _normalise(dt: datetime | None) -> datetime | None:
    """Strip tzinfo so naive comparisons work consistently."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def busy_slots_for(db: AsyncSession, attendee_id: UUID) -> set[datetime]:
    """Slots this attendee already has a meeting_time set for (any non-declined match)."""
    result = await db.execute(
        select(Match.meeting_time, Match.status).where(
            or_(Match.attendee_a_id == attendee_id, Match.attendee_b_id == attendee_id),
            Match.meeting_time.is_not(None),
            Match.status != "declined",
            Match.hidden_by_user.is_(False),
        )
    )
    busy: set[datetime] = set()
    for meeting_time, _status in result.all():
        n = _normalise(meeting_time)
        if n is not None:
            busy.add(n)
    return busy


def free_slots(busy: set[datetime], limit: int | None = None) -> list[datetime]:
    """Bookable slots minus busy. Returns chronological order."""
    free = [s for s in all_slots() if s not in busy]
    return free[:limit] if limit else free


async def mutual_free_slots(
    db: AsyncSession,
    attendee_a_id: UUID,
    attendee_b_id: UUID,
    limit: int = 4,
) -> list[datetime]:
    """Slots free for both attendees — used to render one-click book chips on a match card."""
    busy_a = await busy_slots_for(db, attendee_a_id)
    busy_b = await busy_slots_for(db, attendee_b_id)
    return free_slots(busy_a | busy_b, limit=limit)


async def has_conflict(db: AsyncSession, attendee_id: UUID, when: datetime) -> bool:
    """True if this attendee already has a meeting at `when` (excludes declined / hidden)."""
    target = _normalise(when)
    if target is None:
        return False
    busy = await busy_slots_for(db, attendee_id)
    return target in busy
