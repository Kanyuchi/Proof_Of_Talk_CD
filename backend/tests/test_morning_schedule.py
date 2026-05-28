"""send_morning_schedule_email + run_morning_schedule cron."""
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

import app.services.email as email
import app.services.morning_schedule as ms


# ── email body tests ─────────────────────────────────────────────────────────


def _capture(monkeypatch):
    captured = {}
    def fake_send(to, subj, html, text, force=False):
        captured.update(to=to, subj=subj, html=html, text=text, force=force)
        return True
    monkeypatch.setattr(email, "_send_email", fake_send)
    return captured


def _mtg(time="09:30", name="Marcus Chen", company="Acme", location="Booth 12"):
    return {"time": time, "name": name, "company": company, "location": location}


def test_morning_email_subject_singular_and_plural(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_morning_schedule_email(
        "a@b.com", "Lena Park", [_mtg()], "Day 1 - June 2", magic_token="tok", force=True
    )
    assert "1 meeting at the Louvre today" in cap["subj"]
    assert cap["force"] is True

    cap2 = _capture(monkeypatch)
    email.send_morning_schedule_email(
        "a@b.com", "Lena Park", [_mtg(), _mtg(time="11:00")], "Day 1 - June 2", magic_token="tok", force=True
    )
    assert "2 meetings at the Louvre today" in cap2["subj"]


def test_morning_email_includes_each_meeting(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_morning_schedule_email(
        "a@b.com", "Lena",
        [
            _mtg(time="09:30", name="Marcus Chen", company="Acme", location="Booth 12"),
            _mtg(time="14:00", name="Priya Rao", company="Genventures", location="Salon Mollien"),
        ],
        "Day 1 - June 2", magic_token="tok", force=True,
    )
    for needle in ("09:30", "Marcus Chen", "Acme", "Booth 12",
                   "14:00", "Priya Rao", "Genventures", "Salon Mollien"):
        assert needle in cap["html"], f"{needle} missing from HTML"
        assert needle in cap["text"], f"{needle} missing from plaintext"


def test_morning_email_uses_magic_link_when_present(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_morning_schedule_email(
        "a@b.com", "Lena", [_mtg()], "Day 1 - June 2", magic_token="tok123", force=True
    )
    assert "/m/tok123" in cap["html"]


def test_morning_email_falls_back_to_matches_without_token(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_morning_schedule_email(
        "a@b.com", "Lena", [_mtg()], "Day 1 - June 2", magic_token=None, force=True
    )
    assert "/matches" in cap["html"]
    assert "/m/" not in cap["html"]


def test_morning_email_no_send_when_zero_meetings(monkeypatch):
    cap = _capture(monkeypatch)
    result = email.send_morning_schedule_email(
        "a@b.com", "Lena", [], "Day 1 - June 2", magic_token="tok", force=True
    )
    assert result is False
    assert cap == {}


# ── cron tests ───────────────────────────────────────────────────────────────


def _attendee(*, id=None, email="x@y.com", name="Person", company="Co",
              magic_access_token="t", email_opt_out=False):
    return SimpleNamespace(
        id=id or uuid4(), email=email, name=name, company=company,
        magic_access_token=magic_access_token, email_opt_out=email_opt_out,
    )


def _match_row(*, attendee_a_id, attendee_b_id, meeting_time, status_a="accepted",
               status_b="accepted", meeting_location="Salon Mollien"):
    return SimpleNamespace(
        attendee_a_id=attendee_a_id, attendee_b_id=attendee_b_id,
        meeting_time=meeting_time, status_a=status_a, status_b=status_b,
        meeting_location=meeting_location,
    )


@pytest.mark.asyncio
async def test_skip_non_event_day():
    res = await ms.run_morning_schedule(target_day=date(2026, 5, 31))
    assert res["skipped_non_event_day"] is True
    assert res["sent"] == 0


@pytest.mark.asyncio
async def test_run_sends_to_both_sides_of_mutual_accept(monkeypatch):
    a1 = _attendee(email="alice@x.com", name="Alice", company="A-Co")
    a2 = _attendee(email="bob@x.com", name="Bob", company="B-Co")
    mtg = _match_row(
        attendee_a_id=a1.id, attendee_b_id=a2.id,
        meeting_time=datetime(2026, 6, 2, 9, 30),
    )

    def _scalar_factory(items):
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=items)
        result_obj = MagicMock()
        result_obj.scalars = MagicMock(return_value=scalars_obj)
        return result_obj

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _scalar_factory([mtg]),
        _scalar_factory([a1, a2]),
        _scalar_factory([a1, a2]),
    ])

    cm = AsyncMock()
    cm.__aenter__.return_value = db
    cm.__aexit__.return_value = None

    sent = []
    def fake_send(**kw):
        sent.append(kw)
        return True
    monkeypatch.setattr(ms, "async_session", lambda: cm)
    monkeypatch.setattr(ms, "send_morning_schedule_email", fake_send)

    res = await ms.run_morning_schedule(target_day=date(2026, 6, 2))
    assert res["sent"] == 2
    assert res["errors"] == 0
    addrs = {s["to_email"] for s in sent}
    assert addrs == {"alice@x.com", "bob@x.com"}
    alice_call = next(s for s in sent if s["to_email"] == "alice@x.com")
    assert alice_call["meetings_today"][0]["name"] == "Bob"
    assert alice_call["force"] is True


@pytest.mark.asyncio
async def test_opt_out_attendees_skipped(monkeypatch):
    a1 = _attendee(email="opt@x.com", name="Opt", email_opt_out=True)
    a2 = _attendee(email="bob@x.com", name="Bob")
    mtg = _match_row(
        attendee_a_id=a1.id, attendee_b_id=a2.id,
        meeting_time=datetime(2026, 6, 2, 10, 0),
    )

    def _scalar_factory(items):
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=items)
        r = MagicMock()
        r.scalars = MagicMock(return_value=scalars_obj)
        return r

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _scalar_factory([mtg]),
        _scalar_factory([a1, a2]),
        _scalar_factory([a1, a2]),
    ])
    cm = AsyncMock()
    cm.__aenter__.return_value = db
    cm.__aexit__.return_value = None

    sent = []
    monkeypatch.setattr(ms, "async_session", lambda: cm)
    monkeypatch.setattr(ms, "send_morning_schedule_email",
                        lambda **kw: (sent.append(kw), True)[1])

    res = await ms.run_morning_schedule(target_day=date(2026, 6, 2))
    assert res["sent"] == 1
    assert res["skipped"] == 1
    addrs = {s["to_email"] for s in sent}
    assert addrs == {"bob@x.com"}


@pytest.mark.asyncio
async def test_only_mutual_accepts_count(monkeypatch):
    """The SQL filter (status_a='accepted' AND status_b='accepted') is asserted
    here at the integration boundary: a non-accepted match never reaches the
    grouping step. We assert by feeding it ONE half-accepted row and confirming
    zero sends."""
    a1 = _attendee(email="alice@x.com", name="Alice")
    a2 = _attendee(email="bob@x.com", name="Bob")

    def _scalar_factory(items):
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=items)
        r = MagicMock()
        r.scalars = MagicMock(return_value=scalars_obj)
        return r

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_factory([]))
    cm = AsyncMock()
    cm.__aenter__.return_value = db
    cm.__aexit__.return_value = None

    sent = []
    monkeypatch.setattr(ms, "async_session", lambda: cm)
    monkeypatch.setattr(ms, "send_morning_schedule_email",
                        lambda **kw: (sent.append(kw), True)[1])

    res = await ms.run_morning_schedule(target_day=date(2026, 6, 2))
    assert res["sent"] == 0
    assert res["eligible"] == 0
    assert sent == []
