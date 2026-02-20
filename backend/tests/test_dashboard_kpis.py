"""Tests for dashboard KPI helper calculations."""

from app.api.routes.dashboard import _compute_kpi_rates


def test_compute_kpi_rates_happy_path():
    mutual, scheduled, show = _compute_kpi_rates(
        matches_generated=100,
        mutual_accepted_count=20,
        scheduled_count=10,
        show_count=8,
    )
    assert mutual == 0.2
    assert scheduled == 0.5
    assert show == 0.8


def test_compute_kpi_rates_zero_denominators():
    mutual, scheduled, show = _compute_kpi_rates(
        matches_generated=0,
        mutual_accepted_count=0,
        scheduled_count=0,
        show_count=0,
    )
    assert mutual == 0.0
    assert scheduled == 0.0
    assert show == 0.0
