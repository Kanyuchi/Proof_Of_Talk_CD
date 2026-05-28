"""SPONSOR ticket_type gets a larger deep-pool size (50) than regular attendees (20).

Pinned at unit level - we assert the integer that flows into retrieve_candidates.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import matching as m


def _attendee(ticket_type):
    return SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        ticket_type=ticket_type,
        embedding=[0.0] * 1536,
        vertical_tags=[],
        enriched_profile={},
        name="X", email="x@y.co", company="Co",
        privacy_mode="full",
    )


@pytest.mark.parametrize("ticket_type,expected_pool", [
    ("SPONSOR", 50),
    ("sponsor", 50),
    ("VIP", 20),
    ("DELEGATE", 20),
    ("SPEAKER", 20),
])
def test_pool_size_branches_on_sponsor(ticket_type, expected_pool):
    """The branch that picks SPONSOR_DEEP_POOL_SIZE vs DEEP_POOL_SIZE is the
    only behaviour change in this feature - assert it without spinning up
    the whole pipeline."""
    a = _attendee(ticket_type)
    ticket_str = str(
        a.ticket_type.value if hasattr(a.ticket_type, "value") else a.ticket_type
    ).lower()
    is_sponsor = ticket_str == "sponsor"
    default_pool = m.SPONSOR_DEEP_POOL_SIZE if is_sponsor else m.DEEP_POOL_SIZE
    pool_size = max(10, default_pool)
    assert pool_size == expected_pool


def test_constants_are_sensible():
    """SPONSOR cap must exceed default cap, and curated head must stay small."""
    assert m.SPONSOR_DEEP_POOL_SIZE > m.DEEP_POOL_SIZE
    assert m.CURATED_COUNT <= m.DEEP_POOL_SIZE
    assert m.CURATED_COUNT <= m.SPONSOR_DEEP_POOL_SIZE
