"""send_t_minus_one_reminder_email + run_t_minus_one_reminder cron."""
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.services.email as email
from app.services import t_minus_one_reminder as tm1


# ── email body tests ─────────────────────────────────────────────────────────


def _capture(monkeypatch):
    captured = {}
    def fake_send(to, subj, html, text, force=False):
        captured.update(to=to, subj=subj, html=html, text=text, force=force)
        return True
    monkeypatch.setattr(email, "_send_email", fake_send)
    return captured


def _m(name="Marcus Chen", title="VP", company="Acme"):
    return {"name": name, "title": title, "company": company}


def test_t1_subject(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena Park",
        top_matches=[_m(), _m(name="Priya"), _m(name="Sam")],
        scheduled_count=0, total_matches=10, magic_token="tok", force=True,
    )
    assert "Tomorrow at the Louvre, Lena" in cap["subj"]
    assert cap["force"] is True


def test_t1_includes_top_three_match_names(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena",
        top_matches=[
            _m(name="Marcus Chen", company="Acme"),
            _m(name="Priya Rao", company="Genventures"),
            _m(name="Sam Lee", company="Custody Co"),
        ],
        scheduled_count=2, total_matches=15, magic_token="tok", force=True,
    )
    for needle in ("Marcus Chen", "Priya Rao", "Sam Lee", "Acme", "Genventures", "Custody Co"):
        assert needle in cap["html"], f"missing: {needle}"
        assert needle in cap["text"], f"missing in text: {needle}"


def test_t1_scheduled_count_zero_copy(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena", top_matches=[_m()],
        scheduled_count=0, total_matches=5, magic_token="tok", force=True,
    )
    assert "no meetings booked" in cap["text"].lower()


def test_t1_scheduled_count_one_copy(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena", top_matches=[_m()],
        scheduled_count=1, total_matches=5, magic_token="tok", force=True,
    )
    assert "1 meeting booked" in cap["text"]


def test_t1_scheduled_count_plural_copy(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena", top_matches=[_m()],
        scheduled_count=4, total_matches=8, magic_token="tok", force=True,
    )
    assert "4 meetings booked" in cap["text"]


def test_t1_uses_magic_link(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena", top_matches=[_m()],
        scheduled_count=0, total_matches=5, magic_token="abc123", force=True,
    )
    assert "/m/abc123" in cap["html"]


def test_t1_no_send_when_zero_matches(monkeypatch):
    cap = _capture(monkeypatch)
    result = email.send_t_minus_one_reminder_email(
        "a@b.com", "Lena", top_matches=[],
        scheduled_count=0, total_matches=0, magic_token="tok", force=True,
    )
    assert result is False
    assert cap == {}


# ── cron tests ───────────────────────────────────────────────────────────────


def _attendee(*, id=None, email_addr="x@y.com", name="Person", company="Co",
              title="Title", magic_access_token="t", email_opt_out=False,
              privacy_mode="full"):
    return SimpleNamespace(
        id=id or uuid4(), email=email_addr, name=name, company=company,
        title=title, magic_access_token=magic_access_token,
        email_opt_out=email_opt_out, privacy_mode=privacy_mode,
    )


def _match(*, a, b, tier="curated", status_a="pending", status_b="pending",
           overall_score=0.85, meeting_time=None):
    return SimpleNamespace(
        attendee_a_id=a.id, attendee_b_id=b.id, tier=tier,
        status_a=status_a, status_b=status_b,
        overall_score=overall_score, meeting_time=meeting_time,
        explanation="x",
    )


def _mock_db_two_queries(matches, mutuals, attendees):
    def _scalar_factory(items):
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=items)
        r = MagicMock()
        r.scalars = MagicMock(return_value=scalars_obj)
        return r
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _scalar_factory(matches),     # tier IN (...) query
        _scalar_factory(attendees),   # bulk attendees fetch
        _scalar_factory(mutuals),     # scheduled mutual query
    ])
    cm = AsyncMock()
    cm.__aenter__.return_value = db
    cm.__aexit__.return_value = None
    return cm


@pytest.mark.asyncio
async def test_skip_when_not_target_date(monkeypatch):
    res = await tm1.run_t_minus_one_reminder(target_date=date(2026, 5, 30))
    assert res["skipped_not_t_minus_one_day"] is True
    assert res["sent"] == 0


@pytest.mark.asyncio
async def test_run_sends_to_eligible_attendees(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com")
    bob = _attendee(name="Bob", email_addr="bob@x.com")
    carol = _attendee(name="Carol", email_addr="carol@x.com")
    dan = _attendee(name="Dan", email_addr="dan@x.com")
    eve = _attendee(name="Eve", email_addr="eve@x.com")
    matches = [
        _match(a=alice, b=bob, overall_score=0.9),
        _match(a=alice, b=carol, overall_score=0.85),
        _match(a=alice, b=dan, overall_score=0.80),
        _match(a=alice, b=eve, overall_score=0.75),
    ]
    cm = _mock_db_two_queries(matches, mutuals=[], attendees=[alice, bob, carol, dan, eve])
    monkeypatch.setattr(tm1, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(tm1, "send_t_minus_one_reminder_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await tm1.run_t_minus_one_reminder(target_date=date(2026, 6, 1))
    assert res["sent"] == 5
    assert res["errors"] == 0
    # Alice's email should feature her top 3 by score (Bob, Carol, Dan)
    alice_send = next(s for s in captured if s["to_email"] == "alice@x.com")
    names = [m["name"] for m in alice_send["top_matches"]]
    assert names == ["Bob", "Carol", "Dan"]
    assert alice_send["total_matches"] == 4
    assert alice_send["scheduled_count"] == 0
    assert alice_send["force"] is True


@pytest.mark.asyncio
async def test_scheduled_count_reflects_mutual_bookings(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com")
    bob = _attendee(name="Bob", email_addr="bob@x.com")
    carol = _attendee(name="Carol", email_addr="carol@x.com")
    base_matches = [_match(a=alice, b=bob), _match(a=alice, b=carol)]
    # 1 mutually-accepted booked meeting for Alice (against a 3rd person).
    booked_partner = _attendee(name="X", email_addr="x@x.com")
    mutual = _match(
        a=alice, b=booked_partner,
        status_a="accepted", status_b="accepted",
        meeting_time=datetime(2026, 6, 2, 10, 0),
    )
    # Also include the base matches as "not mutually accepted".
    cm = _mock_db_two_queries(
        base_matches, mutuals=[mutual],
        attendees=[alice, bob, carol, booked_partner],
    )
    monkeypatch.setattr(tm1, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(tm1, "send_t_minus_one_reminder_email",
                        lambda **kw: (captured.append(kw), True)[1])
    await tm1.run_t_minus_one_reminder(target_date=date(2026, 6, 1))
    alice_send = next(s for s in captured if s["to_email"] == "alice@x.com")
    assert alice_send["scheduled_count"] == 1


@pytest.mark.asyncio
async def test_opt_out_attendees_skipped(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com", email_opt_out=True)
    bob = _attendee(name="Bob", email_addr="bob@x.com")
    matches = [_match(a=alice, b=bob)]
    cm = _mock_db_two_queries(matches, [], [alice, bob])
    monkeypatch.setattr(tm1, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(tm1, "send_t_minus_one_reminder_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await tm1.run_t_minus_one_reminder(target_date=date(2026, 6, 1))
    assert "alice@x.com" not in {c["to_email"] for c in captured}
    assert res["sent"] == 1   # bob still sent
    assert res["skipped"] >= 1


@pytest.mark.asyncio
async def test_no_token_skipped(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com", magic_access_token=None)
    bob = _attendee(name="Bob", email_addr="bob@x.com")
    matches = [_match(a=alice, b=bob)]
    cm = _mock_db_two_queries(matches, [], [alice, bob])
    monkeypatch.setattr(tm1, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(tm1, "send_t_minus_one_reminder_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await tm1.run_t_minus_one_reminder(target_date=date(2026, 6, 1))
    assert "alice@x.com" not in {c["to_email"] for c in captured}


@pytest.mark.asyncio
async def test_demo_attendees_skipped(monkeypatch):
    demo = _attendee(name="Demo", email_addr="demo@demo.proofoftalk.io")
    bob = _attendee(name="Bob", email_addr="bob@x.com")
    matches = [_match(a=demo, b=bob)]
    cm = _mock_db_two_queries(matches, [], [demo, bob])
    monkeypatch.setattr(tm1, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(tm1, "send_t_minus_one_reminder_email",
                        lambda **kw: (captured.append(kw), True)[1])
    await tm1.run_t_minus_one_reminder(target_date=date(2026, 6, 1))
    assert "demo@demo.proofoftalk.io" not in {c["to_email"] for c in captured}


@pytest.mark.asyncio
async def test_b2b_only_top_match_uses_company(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com")
    secret = _attendee(name="Real Name", company="Elliptic", privacy_mode="b2b_only")
    other = _attendee(name="Other", company="Other Co")
    matches = [
        _match(a=alice, b=secret, overall_score=0.95),
        _match(a=alice, b=other, overall_score=0.70),
    ]
    cm = _mock_db_two_queries(matches, [], [alice, secret, other])
    monkeypatch.setattr(tm1, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(tm1, "send_t_minus_one_reminder_email",
                        lambda **kw: (captured.append(kw), True)[1])
    await tm1.run_t_minus_one_reminder(target_date=date(2026, 6, 1))
    alice_send = next(s for s in captured if s["to_email"] == "alice@x.com")
    assert alice_send["top_matches"][0]["name"] == "Elliptic"
    assert "Real Name" not in str(alice_send["top_matches"])
