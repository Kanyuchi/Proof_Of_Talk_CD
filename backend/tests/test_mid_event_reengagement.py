"""send_mid_event_reengagement_email + run_mid_event_reengagement cron."""
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.services.email as email
from app.services import mid_event_reengagement as mer


# ── email body tests ─────────────────────────────────────────────────────────


def _capture(monkeypatch):
    captured = {}
    def fake_send(to, subj, html, text, force=False):
        captured.update(to=to, subj=subj, html=html, text=text, force=force)
        return True
    monkeypatch.setattr(email, "_send_email", fake_send)
    return captured


def _m(name="Marcus", title="VP", company="Acme"):
    return {"name": name, "title": title, "company": company}


def test_mer_subject_singular(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_mid_event_reengagement_email(
        "a@b.com", "Lena", new_arrival_count=1,
        top_arrivals=[_m()], magic_token="tok", force=True,
    )
    assert "1 new person just arrived" in cap["subj"]


def test_mer_subject_plural(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_mid_event_reengagement_email(
        "a@b.com", "Lena", new_arrival_count=5,
        top_arrivals=[_m(), _m(name="X"), _m(name="Y")], magic_token="tok", force=True,
    )
    assert "5 new people just arrived" in cap["subj"]


def test_mer_includes_top_three_arrivals(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_mid_event_reengagement_email(
        "a@b.com", "Lena", new_arrival_count=4,
        top_arrivals=[
            _m(name="Marcus Chen", company="Acme"),
            _m(name="Priya Rao", company="Genventures"),
            _m(name="Sam Lee", company="Custody Co"),
        ],
        magic_token="tok", force=True,
    )
    for needle in ("Marcus Chen", "Priya Rao", "Sam Lee", "Acme", "Genventures", "Custody Co"):
        assert needle in cap["html"], f"missing: {needle}"
        assert needle in cap["text"], f"missing in text: {needle}"


def test_mer_uses_magic_link(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_mid_event_reengagement_email(
        "a@b.com", "Lena", new_arrival_count=2,
        top_arrivals=[_m()], magic_token="z123", force=True,
    )
    assert "/m/z123" in cap["html"]


def test_mer_no_send_when_zero(monkeypatch):
    cap = _capture(monkeypatch)
    result = email.send_mid_event_reengagement_email(
        "a@b.com", "Lena", new_arrival_count=0, top_arrivals=[],
        magic_token="tok", force=True,
    )
    assert result is False
    assert cap == {}


# ── cron tests ───────────────────────────────────────────────────────────────


PRE_CUTOFF = datetime(2026, 6, 1, 18, 0, tzinfo=timezone.utc)
POST_CUTOFF = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)


def _attendee(*, id=None, email_addr="x@y.com", name="Person", company="Co",
              title="Title", magic_access_token="t", email_opt_out=False,
              privacy_mode="full", created_at=None):
    return SimpleNamespace(
        id=id or uuid4(), email=email_addr, name=name, company=company,
        title=title, magic_access_token=magic_access_token,
        email_opt_out=email_opt_out, privacy_mode=privacy_mode,
        created_at=created_at if created_at is not None else PRE_CUTOFF,
    )


def _match(*, a, b, tier="curated", status_a="pending", status_b="pending",
           overall_score=0.85):
    return SimpleNamespace(
        attendee_a_id=a.id, attendee_b_id=b.id, tier=tier,
        status_a=status_a, status_b=status_b,
        overall_score=overall_score,
    )


def _mock_db(matches, attendees):
    def _scalar_factory(items):
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=items)
        r = MagicMock()
        r.scalars = MagicMock(return_value=scalars_obj)
        return r
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _scalar_factory(matches),
        _scalar_factory(attendees),
    ])
    cm = AsyncMock()
    cm.__aenter__.return_value = db
    cm.__aexit__.return_value = None
    return cm


@pytest.mark.asyncio
async def test_skip_when_not_target_date(monkeypatch):
    res = await mer.run_mid_event_reengagement(target_date=date(2026, 6, 1))
    assert res["skipped_not_mid_event_day"] is True
    assert res["sent"] == 0


@pytest.mark.asyncio
async def test_fires_only_for_post_cutoff_counterparts(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com", created_at=PRE_CUTOFF)
    old = _attendee(name="OldFriend", email_addr="old@x.com", created_at=PRE_CUTOFF)
    new1 = _attendee(name="New1", email_addr="new1@x.com", created_at=POST_CUTOFF)
    new2 = _attendee(name="New2", email_addr="new2@x.com", created_at=POST_CUTOFF)
    matches = [
        _match(a=alice, b=old, overall_score=0.95),    # pre-cutoff -> skip
        _match(a=alice, b=new1, overall_score=0.90),   # POST -> count
        _match(a=alice, b=new2, overall_score=0.80),   # POST -> count
    ]
    cm = _mock_db(matches, [alice, old, new1, new2])
    monkeypatch.setattr(mer, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(mer, "send_mid_event_reengagement_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mer.run_mid_event_reengagement(target_date=date(2026, 6, 2))
    alice_send = next((s for s in captured if s["to_email"] == "alice@x.com"), None)
    assert alice_send is not None
    assert alice_send["new_arrival_count"] == 2
    names = [a["name"] for a in alice_send["top_arrivals"]]
    assert "OldFriend" not in names
    assert set(names) == {"New1", "New2"}


@pytest.mark.asyncio
async def test_recipients_who_arrived_today_are_skipped(monkeypatch):
    """An attendee who themselves arrived today should NOT get the re-engagement
    blast - they get the first-time match_intro path instead."""
    today_recipient = _attendee(name="Today", email_addr="today@x.com", created_at=POST_CUTOFF)
    arrival = _attendee(name="Arrival", email_addr="arr@x.com", created_at=POST_CUTOFF)
    matches = [_match(a=today_recipient, b=arrival)]
    cm = _mock_db(matches, [today_recipient, arrival])
    monkeypatch.setattr(mer, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(mer, "send_mid_event_reengagement_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mer.run_mid_event_reengagement(target_date=date(2026, 6, 2))
    # Arrival is also pre-existing relative to itself, but skipped because
    # arrival.created_at >= cutoff. today_recipient skipped same reason.
    assert "today@x.com" not in {c["to_email"] for c in captured}


@pytest.mark.asyncio
async def test_already_reviewed_matches_skipped(monkeypatch):
    """If the recipient already responded to the match (status != pending),
    the urgency framing is wrong - skip."""
    alice = _attendee(name="Alice", email_addr="alice@x.com", created_at=PRE_CUTOFF)
    new1 = _attendee(name="New1", email_addr="new1@x.com", created_at=POST_CUTOFF)
    # Alice already declined this match.
    matches = [_match(a=alice, b=new1, status_a="declined")]
    cm = _mock_db(matches, [alice, new1])
    monkeypatch.setattr(mer, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(mer, "send_mid_event_reengagement_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mer.run_mid_event_reengagement(target_date=date(2026, 6, 2))
    assert "alice@x.com" not in {c["to_email"] for c in captured}


@pytest.mark.asyncio
async def test_opt_out_skipped(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com", email_opt_out=True, created_at=PRE_CUTOFF)
    new1 = _attendee(name="New1", email_addr="new1@x.com", created_at=POST_CUTOFF)
    matches = [_match(a=alice, b=new1)]
    cm = _mock_db(matches, [alice, new1])
    monkeypatch.setattr(mer, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(mer, "send_mid_event_reengagement_email",
                        lambda **kw: (captured.append(kw), True)[1])
    await mer.run_mid_event_reengagement(target_date=date(2026, 6, 2))
    assert "alice@x.com" not in {c["to_email"] for c in captured}


@pytest.mark.asyncio
async def test_b2b_only_arrival_uses_company(monkeypatch):
    alice = _attendee(name="Alice", email_addr="alice@x.com", created_at=PRE_CUTOFF)
    secret = _attendee(name="Real Name", company="Elliptic",
                       privacy_mode="b2b_only", created_at=POST_CUTOFF)
    matches = [_match(a=alice, b=secret)]
    cm = _mock_db(matches, [alice, secret])
    monkeypatch.setattr(mer, "async_session", lambda: cm)
    captured = []
    monkeypatch.setattr(mer, "send_mid_event_reengagement_email",
                        lambda **kw: (captured.append(kw), True)[1])
    await mer.run_mid_event_reengagement(target_date=date(2026, 6, 2))
    alice_send = next((s for s in captured if s["to_email"] == "alice@x.com"), None)
    assert alice_send is not None
    assert alice_send["top_arrivals"][0]["name"] == "Elliptic"
    assert "Real Name" not in str(alice_send["top_arrivals"])
