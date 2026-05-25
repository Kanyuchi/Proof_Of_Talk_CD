"""send_interest_notification — 'N people want to meet you' pull-back email."""
import app.services.email as email


def _capture(monkeypatch):
    captured = {}
    def fake_send(to, subj, html, text, force=False):
        captured.update(to=to, subj=subj, html=html, text=text, force=force)
        return True
    monkeypatch.setattr(email, "_send_email", fake_send)
    return captured


def test_subject_plural_and_force_and_deeplink(monkeypatch):
    cap = _capture(monkeypatch)
    ok = email.send_interest_notification(
        "a@b.com", "Marcus Chen", 3, magic_token="tok123", force=True
    )
    assert ok is True
    assert "3 people want to meet you" in cap["subj"]
    assert cap["force"] is True
    assert "/m/tok123?tab=requests" in cap["html"]


def test_subject_singular(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Lena", 1, magic_token="t", force=True)
    assert "1 person wants to meet you" in cap["subj"]


def test_no_token_falls_back_to_matches(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_interest_notification("a@b.com", "Sam", 2, magic_token=None, force=True)
    assert "?tab=requests" not in cap["html"]
    assert "/matches" in cap["html"]
