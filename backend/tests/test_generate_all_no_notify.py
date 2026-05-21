"""Guard: a full match rebuild must NOT email every attendee.

generate_all_matches() wipes + rebuilds matches for the whole pool. Each
per-attendee generation can email an intro to the top match, gated only by
EMAIL_MODE. Once EMAIL_MODE=all, a single rebuild would blast one email per
attendee (739-blast). generate_all_matches must therefore pass notify=False.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.matching import MatchingEngine


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_generate_all_matches_passes_notify_false():
    a1 = SimpleNamespace(id=uuid.uuid4())
    a2 = SimpleNamespace(id=uuid.uuid4())
    db = AsyncMock()
    # execute() #1 = wipe (ignored), #2 = select attendees
    db.execute = AsyncMock(side_effect=[AsyncMock(), _Scalars([a1, a2])])

    eng = MatchingEngine(db)
    eng.process_all_attendees = AsyncMock(return_value=0)
    eng.precompute_candidate_cache = AsyncMock(return_value=None)
    eng.generate_matches_for_attendee = AsyncMock(return_value=[])

    await eng.generate_all_matches(top_k=5)

    assert eng.generate_matches_for_attendee.await_count == 2
    for call in eng.generate_matches_for_attendee.await_args_list:
        assert call.kwargs.get("notify") is False, (
            "bulk rebuild must suppress intro emails"
        )
