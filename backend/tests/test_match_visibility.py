"""Unit tests for the pure tier/visibility logic (no DB)."""
from datetime import datetime, timedelta

from app.services.match_visibility import (
    ViewerMatch,
    tier_limit,
    next_tier_unlock,
    order_and_cap,
)


def test_tier_limits():
    assert tier_limit("SPARSE") == 5
    assert tier_limit("PARTIAL") == 10
    assert tier_limit("GOOD") == 20
    assert tier_limit("???") == 5  # unknown → most conservative


def test_next_tier_unlock():
    assert next_tier_unlock("SPARSE") == 10
    assert next_tier_unlock("PARTIAL") == 20
    assert next_tier_unlock("GOOD") is None


def _vm(score, viewer="pending", other="pending", deferred=None):
    return ViewerMatch(
        match=object(),
        viewer_status=viewer,
        other_status=other,
        viewer_deferred_at=deferred,
        overall_score=score,
    )


def test_review_pool_capped_and_ranked():
    vms = [_vm(0.9), _vm(0.7), _vm(0.5), _vm(0.3)]
    visible, locked = order_and_cap(vms, limit=2)
    assert [v.overall_score for v in visible] == [0.9, 0.7]
    assert locked == 2


def test_deferred_hidden_while_fresh_remains():
    """A deferred card stays out of view as long as at least one fresh review
    item exists - matches the defer_match docstring ("leaves the visible
    window and resurfaces at the back once fresh ones run out"). Before this
    fix, deferred items were merely sorted to the back of fresh and the cap
    rarely actually hid them, so users (David Chapman, Martijn Leentjes, 2026-05-28)
    saw the same cards reappear after clicking "Not now"."""
    t0 = datetime(2026, 5, 21, 10, 0, 0)
    vms = [
        _vm(0.95, deferred=t0),                            # deferred, high score
        _vm(0.60),                                         # fresh, lower score
        _vm(0.50, deferred=t0 + timedelta(minutes=5)),     # deferred later
    ]
    visible, locked = order_and_cap(vms, limit=3)
    # Only fresh is visible; the 2 deferred are hidden (locked).
    assert [round(v.overall_score, 2) for v in visible] == [0.60]
    assert locked == 2


def test_deferred_resurface_when_fresh_runs_out():
    """Once every fresh item has been decided / cleared, the deferred items
    come back (in deferred_at asc order) so the viewer can revisit them."""
    t0 = datetime(2026, 5, 21, 10, 0, 0)
    vms = [
        _vm(0.95, deferred=t0),                            # earlier defer, higher score
        _vm(0.50, deferred=t0 + timedelta(minutes=5)),     # later defer, lower score
    ]
    visible, locked = order_and_cap(vms, limit=5)
    # No fresh exists → deferred resurfaces, ordered by deferred_at ascending.
    assert [round(v.overall_score, 2) for v in visible] == [0.95, 0.50]
    assert locked == 0


def test_incoming_and_committed_always_shown_and_not_capped():
    vms = [
        _vm(0.9, viewer="pending", other="accepted"),  # incoming — always
        _vm(0.8, viewer="accepted", other="pending"),  # committed — always
        _vm(0.7),                                       # review
        _vm(0.6),                                       # review
    ]
    visible, locked = order_and_cap(vms, limit=1)
    scores = {round(v.overall_score, 2) for v in visible}
    assert 0.9 in scores and 0.8 in scores  # incoming + committed survive the cap
    assert 0.7 in scores                     # 1 review shown
    assert locked == 1                       # the 0.6 review row is locked


def test_declined_dropped():
    vms = [_vm(0.9, viewer="declined"), _vm(0.8, other="declined"), _vm(0.7)]
    visible, locked = order_and_cap(vms, limit=10)
    assert [round(v.overall_score, 2) for v in visible] == [0.70]
    assert locked == 0
