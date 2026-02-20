"""Lightweight engagement nudges scheduler (queue-ready abstraction)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendee import Match


@dataclass
class Nudge:
    key: str
    match_id: str
    nudge_type: str
    reason: str
    created_at: str


_DELIVERED_NUDGE_KEYS: set[str] = set()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _make_nudge_key(match: Match, nudge_type: str, now: datetime) -> str:
    bucket = now.strftime("%Y-%m-%d")
    return f"{match.id}:{nudge_type}:{bucket}"


def build_due_nudges(matches: list[Match], now: datetime | None = None) -> list[Nudge]:
    now = now or _utc_now()
    due: list[Nudge] = []

    for m in matches:
        created_at = _as_utc(m.created_at) or now
        meeting_time = _as_utc(m.meeting_time)
        met_at = _as_utc(m.met_at)

        # Pending response nudge after 24h of inactivity.
        if m.status == "pending" and (now - created_at) >= timedelta(hours=24):
            due.append(
                Nudge(
                    key=_make_nudge_key(m, "pending_response", now),
                    match_id=str(m.id),
                    nudge_type="pending_response",
                    reason="Match pending for over 24 hours",
                    created_at=now.isoformat(),
                )
            )

        # Pre-meeting reminder in the 24h window before the booked slot.
        if meeting_time and m.status in {"accepted", "met"} and met_at is None:
            delta = meeting_time - now
            if timedelta(0) <= delta <= timedelta(hours=24):
                due.append(
                    Nudge(
                        key=_make_nudge_key(m, "pre_meeting_reminder", now),
                        match_id=str(m.id),
                        nudge_type="pre_meeting_reminder",
                        reason="Meeting starts within 24 hours",
                        created_at=now.isoformat(),
                    )
                )

        # Post-meeting satisfaction prompt if met but no score captured.
        if met_at and m.satisfaction_score is None and (now - met_at) <= timedelta(hours=72):
            due.append(
                Nudge(
                    key=_make_nudge_key(m, "post_meeting_feedback", now),
                    match_id=str(m.id),
                    nudge_type="post_meeting_feedback",
                    reason="Meeting completed without satisfaction feedback",
                    created_at=now.isoformat(),
                )
            )

    return due


def filter_undelivered(nudges: list[Nudge]) -> list[Nudge]:
    return [n for n in nudges if n.key not in _DELIVERED_NUDGE_KEYS]


def mark_delivered(nudges: list[Nudge]) -> None:
    for n in nudges:
        _DELIVERED_NUDGE_KEYS.add(n.key)


async def compute_due_nudges(db: AsyncSession, now: datetime | None = None) -> list[Nudge]:
    result = await db.execute(select(Match))
    matches = result.scalars().all()
    return build_due_nudges(matches, now=now)


async def trigger_nudges(
    db: AsyncSession,
    dry_run: bool = True,
    now: datetime | None = None,
) -> dict:
    due = await compute_due_nudges(db, now=now)
    ready = filter_undelivered(due)
    if not dry_run:
        mark_delivered(ready)

    return {
        "dry_run": dry_run,
        "total_due": len(due),
        "to_dispatch": len(ready),
        "nudges": [asdict(n) for n in ready[:200]],
    }
