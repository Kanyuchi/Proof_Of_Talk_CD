"""Tests for the _summarise_revenue pure helper in dashboard.py.

TDD: these tests are written BEFORE the helper exists.
Run once to confirm failure, then implement, then confirm green.
"""
import pytest
from app.api.routes.dashboard import _summarise_revenue


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _order(amount, ticket_name="General Pass"):
    """Build a minimal valid-order dict matching Extasy API shape."""
    return {"paymentsAmount": str(amount), "ticketNames": ticket_name}


REAL_PAID_1 = _order(603.00, "Startup Pass")
REAL_PAID_2 = _order(1426.00, "Investor Pass")
EURO_ONE_SPEAKER = _order(1.00, "Speaker Pass")
EURO_ONE_GENERAL = _order(1.00, "General Pass")
EURO_ZERO_COMP = _order(0.00, "VIP Pass")


# ── €1 nominal comp tickets ────────────────────────────────────────────────

def test_euro_one_tickets_not_in_paid_count():
    """185 comp tickets entered as €1 must NOT inflate paid_count."""
    result = _summarise_revenue([EURO_ONE_SPEAKER, EURO_ONE_GENERAL, REAL_PAID_1])
    assert result["paid_count"] == 1, (
        f"Expected 1 paying ticket (€603), got {result['paid_count']}; "
        "€1 tickets must not count as paid"
    )


def test_euro_one_tickets_not_in_paid_revenue():
    """€1 ticket revenue must not feed the avg-ticket numerator."""
    result = _summarise_revenue([EURO_ONE_SPEAKER, REAL_PAID_1])
    assert result["paid_revenue"] == pytest.approx(603.00), (
        f"paid_revenue should be €603, got {result['paid_revenue']}"
    )


def test_euro_one_tickets_are_counted_as_comp():
    """€1 tickets must land in comp_count, not paid_count."""
    result = _summarise_revenue([EURO_ONE_SPEAKER, EURO_ONE_GENERAL, REAL_PAID_1])
    assert result["comp_count"] == 2, (
        f"Expected 2 comp tickets (the two €1 rows), got {result['comp_count']}"
    )


def test_euro_one_tickets_included_in_total_revenue():
    """€1 tickets were sold — their €1 must still appear in total_revenue."""
    result = _summarise_revenue([EURO_ONE_SPEAKER, EURO_ONE_GENERAL, REAL_PAID_1])
    assert result["total_revenue"] == pytest.approx(605.00), (
        f"total_revenue should be €605 (603 + 1 + 1), got {result['total_revenue']}"
    )


# ── €0 comp tickets ────────────────────────────────────────────────────────

def test_zero_amount_is_comp_not_paid():
    result = _summarise_revenue([EURO_ZERO_COMP, REAL_PAID_1])
    assert result["paid_count"] == 1
    assert result["comp_count"] == 1


def test_zero_amount_adds_nothing_to_total_revenue():
    result = _summarise_revenue([EURO_ZERO_COMP, REAL_PAID_1])
    assert result["total_revenue"] == pytest.approx(603.00)


# ── Average paid-ticket calculation ───────────────────────────────────────

def test_avg_ticket_excludes_comp():
    """avg_ticket = paid_revenue / paid_count, ignoring €0 and €1 rows."""
    result = _summarise_revenue([
        REAL_PAID_1,        # €603
        REAL_PAID_2,        # €1426
        EURO_ONE_SPEAKER,   # €1  ← comp
        EURO_ZERO_COMP,     # €0  ← comp
    ])
    expected_avg = (603.00 + 1426.00) / 2
    assert result["avg_ticket"] == pytest.approx(expected_avg, rel=1e-4), (
        f"avg_ticket should be {expected_avg:.2f}, got {result['avg_ticket']}"
    )


def test_avg_ticket_is_zero_when_no_paid():
    """If there are only comp tickets, avg_ticket must be 0 (not a ZeroDivisionError)."""
    result = _summarise_revenue([EURO_ZERO_COMP, EURO_ONE_SPEAKER])
    assert result["avg_ticket"] == 0.0


# ── by_type grouping ────────────────────────────────────────────────────────

def test_by_type_revenue_preserved():
    """by_type must include ALL valid orders' revenue (comp + paid alike)."""
    result = _summarise_revenue([EURO_ONE_SPEAKER, REAL_PAID_1])
    by_type = result["by_type"]
    speaker_row = next((r for r in by_type if r["type"] == "Speaker Pass"), None)
    startup_row = next((r for r in by_type if r["type"] == "Startup Pass"), None)
    assert speaker_row is not None, "Speaker Pass must appear in by_type"
    assert startup_row is not None, "Startup Pass must appear in by_type"
    assert speaker_row["revenue"] == pytest.approx(1.00)
    assert startup_row["revenue"] == pytest.approx(603.00)


def test_by_type_count_preserved():
    """Each ticket type's count must reflect all orders (not just paid ones)."""
    result = _summarise_revenue([EURO_ONE_SPEAKER, EURO_ONE_SPEAKER, REAL_PAID_1])
    by_type = result["by_type"]
    speaker_row = next(r for r in by_type if r["type"] == "Speaker Pass")
    assert speaker_row["count"] == 2


# ── Production scenario (post-fix expected values) ────────────────────────

def test_production_scenario():
    """Simulate 185 speaker comps + 123 real-paid tickets.
    Asserts the post-fix headline numbers match the spec.
    """
    orders = []
    # 178 Speaker Pass @ €1 + 7 General Pass @ €1 = 185 comp
    orders += [_order(1.00, "Speaker Pass")] * 178
    orders += [_order(1.00, "General Pass")] * 7
    # 123 real-paid tickets at ~€1,507 avg → total paid_revenue ≈ €185,371
    # Use a round number close to the real avg so the assertion is exact.
    orders += [_order(1507.00, "Investor Pass")] * 123

    result = _summarise_revenue(orders)

    assert result["comp_count"] == 185
    assert result["paid_count"] == 123
    assert result["total_revenue"] == pytest.approx(185 + 123 * 1507.00, rel=1e-6)
    # avg must be ~€1,507, not ~€603 (the broken value)
    assert result["avg_ticket"] == pytest.approx(1507.00, rel=1e-4)
    assert result["avg_ticket"] > 1000, (
        f"avg_ticket {result['avg_ticket']:.2f} still looks wrong (should be > €1000)"
    )
