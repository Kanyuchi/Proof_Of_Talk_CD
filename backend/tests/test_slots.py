"""Tests for conference slot availability helpers (services/slots.py).

Focus: `mutual_free_slots(..., limit=None)` must return the COMPLETE set of
both-parties-free slots so the match-card picker can grey out already-booked
times, while the default `limit=4` still drives the chip preview.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.services import slots
from app.services.slots import all_slots, free_slots, mutual_free_slots


def test_free_slots_uncapped_returns_everything():
    """limit=None returns all bookable slots minus busy; limit=4 truncates."""
    busy = {datetime(2026, 6, 2, 9, 0)}
    full = free_slots(busy, limit=None)
    assert datetime(2026, 6, 2, 9, 0) not in full
    # All other slots survive (27 total - 1 busy = 26).
    assert len(full) == len(all_slots()) - 1
    # The default chip-preview cap still works.
    assert len(free_slots(busy, limit=4)) == 4


@pytest.mark.asyncio
async def test_mutual_free_slots_uncapped_returns_all_non_busy():
    """Two attendees busy at different times: limit=None drops BOTH busy slots
    and returns everything else (more than the 4-slot chip preview)."""
    a_id, b_id = "A", "B"
    busy_a = {datetime(2026, 6, 2, 16, 0)}  # A booked at 16:00
    busy_b = {datetime(2026, 6, 2, 18, 30)}  # B booked at 18:30

    async def fake_busy(_db, attendee_id):
        return busy_a if attendee_id == a_id else busy_b

    with patch.object(slots, "busy_slots_for", side_effect=fake_busy):
        free = await mutual_free_slots(AsyncMock(), a_id, b_id, limit=None)

    # Neither party's booked slot is offered.
    assert datetime(2026, 6, 2, 16, 0) not in free
    assert datetime(2026, 6, 2, 18, 30) not in free
    # Uncapped result is the full grid minus the two busy slots — and crucially
    # longer than the 4-slot chip preview, which is the whole point of the fix.
    assert len(free) == len(all_slots()) - 2
    assert len(free) > 4


@pytest.mark.asyncio
async def test_mutual_free_slots_default_limit_is_chip_preview():
    """Default limit=4 powers the 'Both free at' chip preview, unchanged."""
    async def fake_busy(_db, _attendee_id):
        return set()

    with patch.object(slots, "busy_slots_for", side_effect=fake_busy):
        preview = await mutual_free_slots(AsyncMock(), "A", "B")

    assert len(preview) == 4
