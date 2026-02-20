"""Tests for engagement nudge scheduling and idempotency."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.engagement import (
    build_due_nudges,
    filter_undelivered,
    mark_delivered,
)


def _match(**overrides):
    now = datetime.now(timezone.utc)
    base = {
        "id": "m1",
        "status": "pending",
        "created_at": now - timedelta(days=2),
        "meeting_time": None,
        "met_at": None,
        "satisfaction_score": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_due_nudges_detects_pending_and_feedback_cases():
    now = datetime.now(timezone.utc)
    pending = _match(id="m-pending", status="pending", created_at=now - timedelta(days=2))
    post_meeting = _match(
        id="m-met",
        status="met",
        met_at=now - timedelta(hours=2),
        meeting_time=now - timedelta(hours=3),
        satisfaction_score=None,
    )
    due = build_due_nudges([pending, post_meeting], now=now)
    types = {n.nudge_type for n in due}
    assert "pending_response" in types
    assert "post_meeting_feedback" in types


def test_idempotent_filtering_after_mark_delivered():
    now = datetime.now(timezone.utc)
    pending = _match(id="m-idem", status="pending", created_at=now - timedelta(days=2))
    due = build_due_nudges([pending], now=now)
    first = filter_undelivered(due)
    assert len(first) == 1
    mark_delivered(first)
    second = filter_undelivered(due)
    assert len(second) == 0
