import asyncio, uuid
from unittest.mock import AsyncMock, patch
import pytest
from app.models.attendee import Attendee
from app.services.matching import MatchingEngine


def _attendee(**kw):
    a = Attendee(id=uuid.uuid4(), name="T", email="t@x.co", company="C")
    a.ai_summary = "ORIGINAL USER TEXT"
    for k, v in kw.items():
        setattr(a, k, v)
    return a


@pytest.mark.asyncio
async def test_process_attendee_preserves_pinned_summary():
    a = _attendee(ai_summary_pinned=True)
    eng = MatchingEngine(db=AsyncMock())
    with patch("app.services.matching.generate_ai_summary", new=AsyncMock(return_value="AI REWRITE")) as gen, \
         patch("app.services.matching.classify_intents", new=AsyncMock(return_value=["knowledge_exchange"])), \
         patch("app.services.matching.infer_customer_profile", new=AsyncMock(return_value={})), \
         patch("app.services.matching.embed_attendee", new=AsyncMock(return_value=[0.0])):
        await eng.process_attendee(a)
    gen.assert_not_called()
    assert a.ai_summary == "ORIGINAL USER TEXT"


@pytest.mark.asyncio
async def test_process_attendee_regenerates_when_not_pinned():
    a = _attendee(ai_summary_pinned=False)
    eng = MatchingEngine(db=AsyncMock())
    with patch("app.services.matching.generate_ai_summary", new=AsyncMock(return_value="AI REWRITE")), \
         patch("app.services.matching.classify_intents", new=AsyncMock(return_value=["knowledge_exchange"])), \
         patch("app.services.matching.infer_customer_profile", new=AsyncMock(return_value={})), \
         patch("app.services.matching.embed_attendee", new=AsyncMock(return_value=[0.0])):
        await eng.process_attendee(a)
    assert a.ai_summary == "AI REWRITE"
