# backend/tests/test_profile_pipeline.py
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.profile_pipeline as pp


def _fake_session(db):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


@pytest.mark.asyncio
async def test_refresh_profile_matches_reembeds_then_matches():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid)
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    engine = MagicMock()
    engine.process_attendee = AsyncMock()
    engine.generate_matches_for_attendee = AsyncMock()
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "MatchingEngine", MagicMock(return_value=engine)):
        await pp.refresh_profile_matches(aid)
    engine.process_attendee.assert_awaited_once_with(attendee)
    engine.generate_matches_for_attendee.assert_awaited_once_with(
        aid, top_k=10, notify=False
    )


@pytest.mark.asyncio
async def test_refresh_profile_matches_noop_when_attendee_missing():
    aid = uuid.uuid4()
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    engine = MagicMock()
    engine.process_attendee = AsyncMock()
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "MatchingEngine", MagicMock(return_value=engine)):
        await pp.refresh_profile_matches(aid)
    engine.process_attendee.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_full_enrichment_enriches_then_refreshes():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid, enriched_profile={})
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    svc = MagicMock()
    svc.enrich_attendee = AsyncMock(return_value={"grid": {"x": 1}})
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "EnrichmentService", MagicMock(return_value=svc)), \
         patch.object(pp, "refresh_profile_matches", AsyncMock()) as refresh:
        await pp.run_full_enrichment(aid)
    svc.enrich_attendee.assert_awaited_once_with(attendee)
    assert attendee.enriched_profile == {"grid": {"x": 1}}
    refresh.assert_awaited_once_with(aid)


@pytest.mark.asyncio
async def test_run_full_enrichment_still_refreshes_when_enrich_fails():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid, enriched_profile={})
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    svc = MagicMock()
    svc.enrich_attendee = AsyncMock(side_effect=RuntimeError("grid down"))
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "EnrichmentService", MagicMock(return_value=svc)), \
         patch.object(pp, "refresh_profile_matches", AsyncMock()) as refresh:
        await pp.run_full_enrichment(aid)
    refresh.assert_awaited_once_with(aid)
