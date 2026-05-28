"""Tier-based match visibility — the enrichment-gated unlock cap + defer ordering.

Pure functions (no DB, no I/O) so the cap and ordering stay unit-testable.
The completeness *tier* itself comes from concierge.profile_data_quality();
this module only maps that tier to a limit and orders the per-viewer pool.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Profiles shown per completeness tier (deeper-match-pool spec, 2026-05-21).
TIER_LIMITS: dict[str, int] = {"SPARSE": 5, "PARTIAL": 10, "GOOD": 20}
_TIER_ORDER = ["SPARSE", "PARTIAL", "GOOD"]


def tier_limit(tier: str) -> int:
    """How many review-pool matches a viewer in `tier` may see."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["SPARSE"])


def next_tier_unlock(tier: str) -> int | None:
    """Total review matches visible at the NEXT tier up, or None if already GOOD."""
    try:
        i = _TIER_ORDER.index(tier)
    except ValueError:
        i = 0
    if i >= len(_TIER_ORDER) - 1:
        return None
    return TIER_LIMITS[_TIER_ORDER[i + 1]]


@dataclass
class ViewerMatch:
    """A match row oriented from one viewer's perspective."""
    match: object               # the SQLAlchemy Match row (opaque to this module)
    viewer_status: str          # this viewer's status_a/status_b value
    other_status: str           # the counterparty's status value
    viewer_deferred_at: datetime | None
    overall_score: float


def order_and_cap(vms: list[ViewerMatch], limit: int) -> tuple[list[ViewerMatch], int]:
    """Order a viewer's matches and apply the tier cap to the review pool.

    Returns ``(visible, locked_count)``.

    - Incoming requests (viewer pending, other accepted) are always shown.
    - Committed matches (viewer accepted/met) are always shown.
    - Declined on either side are dropped.
    - Review pool (viewer pending, other not accepted): fresh by score desc,
      then deferred by deferred_at asc; capped to ``limit``. The remainder
      becomes ``locked_count``.
    """
    incoming: list[ViewerMatch] = []
    committed: list[ViewerMatch] = []
    review: list[ViewerMatch] = []
    for v in vms:
        if v.viewer_status == "declined" or v.other_status == "declined":
            continue
        if v.viewer_status in ("accepted", "met"):
            committed.append(v)
        elif v.viewer_status == "pending" and v.other_status == "accepted":
            incoming.append(v)
        else:
            review.append(v)

    incoming.sort(key=lambda v: v.overall_score, reverse=True)
    committed.sort(key=lambda v: v.overall_score, reverse=True)
    fresh = sorted(
        [v for v in review if v.viewer_deferred_at is None],
        key=lambda v: v.overall_score,
        reverse=True,
    )
    deferred = sorted(
        [v for v in review if v.viewer_deferred_at is not None],
        key=lambda v: v.viewer_deferred_at,
    )
    # Deferred cards stay hidden while any fresh review item exists; they
    # resurface (ordered by deferred_at asc) only once fresh is exhausted.
    # Sorting deferred to the back of fresh + applying the cap rarely actually
    # hid them - review pools usually fit under the limit, so the same cards
    # kept reappearing after "Not now" (David Chapman, 2026-05-28).
    review_ordered = fresh if fresh else deferred
    shown_review = review_ordered[:limit]
    locked = (len(fresh) + len(deferred)) - len(shown_review)
    visible = incoming + shown_review + committed
    return visible, locked
