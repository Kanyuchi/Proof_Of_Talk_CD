"""Tests for status transitions and feedback update behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from app.api.routes.matches import _compute_overall_status, update_meeting_feedback


def test_overall_status_declined_takes_precedence():
    assert _compute_overall_status("accepted", "declined") == "declined"


def test_overall_status_met_when_both_mark_met():
    assert _compute_overall_status("met", "met") == "met"


def test_overall_status_accepted_for_accepted_met_combo():
    assert _compute_overall_status("accepted", "met") == "accepted"


@pytest.mark.asyncio
async def test_feedback_update_clamps_satisfaction():
    match = SimpleNamespace(
        id="m1",
        meeting_outcome=None,
        satisfaction_score=None,
        met_at=None,
        hidden_by_user=False,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=match)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    data = SimpleNamespace(
        meeting_outcome="met",
        satisfaction_score=7,
        met_at=None,
        hidden_by_user=True,
    )
    with patch("app.api.routes.matches.MatchResponse.model_validate", side_effect=lambda m: m):
        out = await update_meeting_feedback("m1", data, db, _user=SimpleNamespace())
    assert out.satisfaction_score == 5.0
    assert out.hidden_by_user is True
