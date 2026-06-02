"""Tests for conference slot availability helpers (services/slots.py).

Focus: `mutual_free_slots(..., limit=None)` must return the COMPLETE set of
both-parties-free slots so the match-card picker can grey out already-booked
times, while the default `limit=4` still drives the chip preview.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.services import slots
from app.services.slots import (
    all_slots,
    free_slots,
    mutual_free_slots,
    normalise_location,
    MEETING_LOCATIONS,
    DEFAULT_MEETING_LOCATION,
)


def test_normalise_location_accepts_known_spots():
    """Each floor-plan spot is preserved verbatim."""
    for loc in MEETING_LOCATIONS:
        assert normalise_location(loc) == loc
    # Surrounding whitespace is tolerated.
    assert normalise_location(f"  {MEETING_LOCATIONS[1]}  ") == MEETING_LOCATIONS[1]


def test_normalise_location_falls_back_to_default():
    """Empty/None/unknown values collapse to the default spot, never junk."""
    assert normalise_location(None) == DEFAULT_MEETING_LOCATION
    assert normalise_location("") == DEFAULT_MEETING_LOCATION
    assert normalise_location("Some Random Room") == DEFAULT_MEETING_LOCATION


# Anchor "now" before the conference so past-slot filtering is a no-op and these
# tests stay deterministic regardless of the wall-clock they run at.
BEFORE_EVENT = datetime(2026, 6, 1, 0, 0)


def test_free_slots_uncapped_returns_everything():
    """limit=None returns all bookable slots minus busy; limit=4 truncates."""
    busy = {datetime(2026, 6, 2, 9, 0)}
    full = free_slots(busy, limit=None, now=BEFORE_EVENT)
    assert datetime(2026, 6, 2, 9, 0) not in full
    # All other slots survive (full grid - 1 busy).
    assert len(full) == len(all_slots()) - 1
    # The default chip-preview cap still works.
    assert len(free_slots(busy, limit=4, now=BEFORE_EVENT)) == 4


def test_free_slots_drops_past_slots():
    """Slots that have already started (relative to `now`) are never offered."""
    # Mid-conference: 12:30 on June 2 — morning slots gone, 13:00 onward survive.
    now = datetime(2026, 6, 2, 12, 30)
    free = free_slots(set(), limit=None, now=now)
    assert datetime(2026, 6, 2, 9, 0) not in free
    assert datetime(2026, 6, 2, 11, 30) not in free
    assert datetime(2026, 6, 2, 13, 0) in free  # next bookable today
    assert datetime(2026, 6, 3, 9, 0) in free   # tomorrow untouched


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
        free = await mutual_free_slots(AsyncMock(), a_id, b_id, limit=None, now=BEFORE_EVENT)

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
        preview = await mutual_free_slots(AsyncMock(), "A", "B", now=BEFORE_EVENT)

    assert len(preview) == 4
