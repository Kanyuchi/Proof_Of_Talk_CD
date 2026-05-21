"""Tests for the deep-pool / defer feature: model columns, defer route, deep ranking."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.attendee import Match


def test_match_has_tier_and_deferral_columns():
    m = Match()
    # Defaults are applied at flush time; the attributes must at least exist.
    assert hasattr(m, "tier")
    assert hasattr(m, "deferred_a_at")
    assert hasattr(m, "deferred_b_at")
    # Column metadata is correct.
    cols = Match.__table__.c
    assert cols["tier"].default.arg == "curated"
    assert cols["deferred_a_at"].nullable is True
    assert cols["deferred_b_at"].nullable is True
