"""send_interest_notification - count-tiered "N people want to meet you" email."""
import app.services.email as email


def _capture(monkeypatch):
    captured = {}
    def fake_send(to, subj, html, text, force=False):
        captured.update(to=to, subj=subj, html=html, text=text, force=force)
        return True
    monkeypatch.setattr(email, "_send_email", fake_send)
    return captured


# ── tier 1: count == 1 (soft) ────────────────────────────────────────────────


def test_tier_soft_subject_and_copy(monkeypatch):
    cap = _capture(monkeypatch)
    ok = email.send_interest_notification(
        "a@b.com", "Lena", 1, magic_token="t", force=True
    )
    assert ok is True
    # Soft tier doesn't use a count in the subject — "Someone wants to meet you".
    assert "Someone wants to meet you" in cap["subj"]
    assert "1 person" not in cap["subj"]
    # Lead text refers to "an attendee" not "1 person".
    assert "an attendee just said yes" in cap["html"]
    assert "Lena" in cap["html"]
    # CTA copy is the low-key version.
    assert "See who it is" in cap["html"]
    assert cap["force"] is True


# ── tier 2: 2 <= count <= 4 (standard) ───────────────────────────────────────


def test_tier_standard_subject_and_copy(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Marcus", 3, magic_token="tok123", force=True)
    assert "3 people want to meet you at Proof of Talk" in cap["subj"]
    assert "Marcus" in cap["html"]
    assert "3 people want to meet you at Proof of Talk 2026" in cap["html"]
    assert "/m/tok123?tab=requests" in cap["html"]
    # Standard tier CTA
    assert "See who wants to meet you" in cap["html"]


def test_tier_standard_lower_bound(monkeypatch):
    """count == 2 must fall into the standard tier, not the soft tier."""
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Sam", 2, magic_token="t", force=True)
    assert "2 people want to meet you" in cap["subj"]
    assert "Someone wants" not in cap["subj"]


def test_tier_standard_upper_bound(monkeypatch):
    """count == 4 stays in the standard tier, not urgency."""
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Sam", 4, magic_token="t", force=True)
    assert "4 people want to meet you at Proof of Talk" in cap["subj"]
    assert "days away" not in cap["subj"]


# ── tier 3: count >= 5 (urgency) ─────────────────────────────────────────────


def test_tier_urgency_subject_and_copy(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Priya", 12, magic_token="t", force=True)
    # Urgency tier subject names the Louvre + timing
    assert "12 people want to meet you" in cap["subj"]
    assert "days away" in cap["subj"]
    # Heading shifts to "waiting on you" framing
    assert "12 people are waiting on you" in cap["html"]
    # Body refers to Tuesday morning + acceptance urgency
    assert "Tuesday morning" in cap["html"]
    assert "Respond to all 12" in cap["html"]


def test_tier_urgency_lower_bound(monkeypatch):
    """count == 5 is the urgency tier floor."""
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "X", 5, magic_token="t", force=True)
    assert "5 people want to meet you" in cap["subj"]
    assert "days away" in cap["subj"]


# ── shared invariants across all tiers ───────────────────────────────────────


def test_no_token_falls_back_to_matches(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Sam", 2, magic_token=None, force=True)
    assert "?tab=requests" not in cap["html"]
    assert "/matches" in cap["html"]


def test_force_flag_propagated_across_tiers(monkeypatch):
    for count in (1, 3, 8):
        cap = _capture(monkeypatch)
        email.send_interest_notification("a@b.com", "X", count, magic_token="t", force=True)
        assert cap["force"] is True


def test_text_body_contains_requests_url_in_each_tier(monkeypatch):
    for count in (1, 3, 8):
        cap = _capture(monkeypatch)
        email.send_interest_notification("a@b.com", "X", count, magic_token="t", force=True)
        assert "/m/t?tab=requests" in cap["text"]
