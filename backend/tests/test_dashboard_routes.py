"""Regression tests for dashboard route edge cases."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks

from app.api.routes.dashboard import matches_by_type, trigger_matching


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_matches_by_type_no_missing_matched_attendee_id():
    """Route should build pair labels from attendee_a_id/attendee_b_id."""
    match = SimpleNamespace(
        id="m-1",
        attendee_a_id="a-1",
        attendee_b_id="b-1",
        overall_score=0.82,
        explanation="Strong strategic fit",
        match_type="complementary",
        status="pending",
    )
    attendee_a = SimpleNamespace(id="a-1", name="Alice")
    attendee_b = SimpleNamespace(id="b-1", name="Bob")

    db = AsyncMock()
    db.execute.return_value = _ScalarResult([match])
    db.get = AsyncMock(side_effect=[attendee_a, attendee_b])

    out = await matches_by_type("complementary", 20, db, _user=SimpleNamespace())
    assert out["total"] == 1
    assert out["matches"][0]["matched_attendee"]["name"] == "Alice ↔ Bob"


@pytest.mark.asyncio
async def test_trigger_matching_registers_background_task():
    """Route should schedule the matching pipeline task and return metadata."""
    attendees = [SimpleNamespace(id="a"), SimpleNamespace(id="b"), SimpleNamespace(id="c")]
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(attendees)
    bg = BackgroundTasks()

    out = await trigger_matching(bg, db, admin=SimpleNamespace(is_admin=True))
    assert out["status"] == "started"
    assert out["attendees_processed"] == 3
    assert out["top_k"] >= 1
    assert out["total_matches"] >= 3
    assert len(bg.tasks) == 1
