"""send_reengagement_email + the tracking_options plumbing it depends on."""
from unittest.mock import MagicMock

import app.services.email as email


def _mock_resend_ok(monkeypatch):
    """Patch httpx.post to capture the Resend payload and return 200."""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        m = MagicMock()
        m.status_code = 200
        return m

    monkeypatch.setattr(email.httpx, "post", fake_post)
    monkeypatch.setattr(email, "get_settings", lambda: _settings())
    return captured


def _settings():
    """Minimal settings stand-in: API key set, EMAIL_MODE doesn't matter because
    every call below uses force=True."""
    return MagicMock(
        RESEND_API_KEY="test_key",
        RESEND_FROM_EMAIL="Proof of Talk <team@xventures.de>",
        EMAIL_MODE="off",
        EMAIL_ALLOWLIST="",
        EMAIL_REPLY_TO="team@xventures.de",
        APP_PUBLIC_URL="https://meet.proofoftalk.io",
    )


def test_send_email_passes_tracking_options_when_provided(monkeypatch):
    """tracking_options dict must land in the Resend payload verbatim."""
    captured = _mock_resend_ok(monkeypatch)

    ok = email._send_email(
        to_email="test@proofoftalk.io",
        subject="hi",
        html="<p>hi</p>",
        force=True,
        tracking_options={"open_tracking": True, "click_tracking": True},
    )

    assert ok is True
    assert captured["payload"]["tracking_options"] == {
        "open_tracking": True,
        "click_tracking": True,
    }


def test_send_email_omits_tracking_options_when_not_provided(monkeypatch):
    """No tracking_options key in payload when None - preserves prior behaviour."""
    captured = _mock_resend_ok(monkeypatch)

    email._send_email(
        to_email="test@proofoftalk.io",
        subject="hi",
        html="<p>hi</p>",
        force=True,
    )

    assert "tracking_options" not in captured["payload"]


# ── send_reengagement_email ──────────────────────────────────────────────────


def test_send_reengagement_email_uses_reciprocity_subject_when_incoming_gt_zero(monkeypatch):
    captured = _mock_resend_ok(monkeypatch)

    ok = email.send_reengagement_email(
        to_email="william@blockcomp.io",
        attendee_name="William Sample",
        first_name="William",
        total_matches=16,
        incoming_interest_count=3,
        top_matches=[
            {"name": "Aylin Z", "title": "VP", "company": "Elliptic"},
            {"name": "Ylli V", "title": "CTO", "company": "Elliptic"},
        ],
        magic_token="tok_xyz",
        force=True,
    )

    assert ok is True
    assert captured["payload"]["subject"] == "3 people want to meet you at Proof of Talk"
    assert "Aylin Z" in captured["payload"]["html"]
    assert "Ylli V" in captured["payload"]["html"]
    assert "tok_xyz" in captured["payload"]["html"]
    assert captured["payload"]["tracking_options"] == {
        "open_tracking": True,
        "click_tracking": True,
    }


def test_send_reengagement_email_uses_match_count_subject_when_no_incoming(monkeypatch):
    captured = _mock_resend_ok(monkeypatch)

    email.send_reengagement_email(
        to_email="x@y.com",
        attendee_name="William Sample",
        first_name="William",
        total_matches=16,
        incoming_interest_count=0,
        top_matches=[{"name": "Aylin", "title": "VP", "company": "Elliptic"}],
        magic_token="tok",
        force=True,
    )

    assert captured["payload"]["subject"] == "Your 16 matches at the Louvre, this Tuesday"


def test_send_reengagement_email_returns_false_when_no_top_matches(monkeypatch):
    """No teaser cards = no honest send."""
    posted = []

    def fake_post(url, headers=None, json=None, timeout=None):
        posted.append(json)
        m = MagicMock()
        m.status_code = 200
        return m

    monkeypatch.setattr(email.httpx, "post", fake_post)
    monkeypatch.setattr(email, "get_settings", lambda: _settings())

    ok = email.send_reengagement_email(
        to_email="x@y.com",
        attendee_name="A",
        first_name="A",
        total_matches=0,
        incoming_interest_count=0,
        top_matches=[],
        magic_token="tok",
        force=True,
    )
    assert ok is False
    assert posted == []
