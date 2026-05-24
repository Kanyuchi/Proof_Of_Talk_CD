"""Tests for the _linkedin_pending pure helper in dashboard.py.

TDD: written BEFORE the helper exists. Run once to confirm failure, then
implement, then confirm green.

Background (2026-05-24): the dashboard's "N attendees pending LinkedIn
enrichment" banner read 90 but the real actionable backlog was ~2. The old
formula counted any row with a URL and no `linkedin.headline`, which swept in
three non-actionable buckets:
  - 48 rows flagged `linkedin_unscrapable` (concluded dead after repeated 403s)
  - 26 empty-stub scrapes (attempted, returned nothing — `linkedin_enriched_at`
    set but headline/summary/experiences all empty; re-scraping yields nothing)
  - 7 seeded demo personas (`@demo.proofoftalk.io`, fake `-demo` URLs)
`_linkedin_pending` excludes all three so the banner reflects true backlog.
"""
from types import SimpleNamespace

from app.api.routes.dashboard import _linkedin_pending


def _att(linkedin_url="https://www.linkedin.com/in/jane", enriched_profile=None,
         email="jane@example.com"):
    return SimpleNamespace(
        linkedin_url=linkedin_url,
        enriched_profile=enriched_profile or {},
        email=email,
    )


# ── Counts as pending ───────────────────────────────────────────────────────

def test_genuine_never_scraped_is_pending():
    """URL set, never touched, real attendee → actionable backlog."""
    assert _linkedin_pending(_att()) is True


def test_malformed_url_still_pending():
    """A junk URL string we have never attempted is still 'has URL, untried'.

    URL cleanup is a separate, deferred fix; the banner should still surface it.
    """
    assert _linkedin_pending(_att(linkedin_url="N/A")) is True


# ── Excluded from pending ───────────────────────────────────────────────────

def test_no_url_not_pending():
    assert _linkedin_pending(_att(linkedin_url=None)) is False


def test_already_enriched_not_pending():
    """Truthy headline is the success marker — nothing left to do."""
    a = _att(enriched_profile={"linkedin": {"headline": "CEO at Acme"},
                               "linkedin_enriched_at": "2026-05-01T00:00:00"})
    assert _linkedin_pending(a) is False


def test_flagged_unscrapable_not_pending():
    """Concluded dead after repeated failures — not actionable."""
    a = _att(enriched_profile={"linkedin_unscrapable": "verification_failed"})
    assert _linkedin_pending(a) is False


def test_empty_stub_attempt_not_pending():
    """Attempted, returned nothing (private/login-walled): re-scrape is futile.

    linkedin_enriched_at set, but headline/summary/experiences all empty.
    """
    a = _att(enriched_profile={
        "linkedin_enriched_at": "2026-05-10T00:00:00",
        "linkedin": {"headline": None, "summary": "", "experiences": []},
    })
    assert _linkedin_pending(a) is False


def test_demo_persona_not_pending():
    """Seeded video-demo personas have fake URLs and must not inflate ops."""
    a = _att(email="marcus@demo.proofoftalk.io",
             linkedin_url="https://www.linkedin.com/in/marcus-chen-demo")
    assert _linkedin_pending(a) is False


def test_missing_email_does_not_crash():
    """email=None must be handled (None.endswith would raise)."""
    assert _linkedin_pending(_att(email=None)) is True
