"""send_match_digest_email + run_match_digest cron."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.services.email as email
from app.services import match_digest_cron as mdc


# ── email body tests ─────────────────────────────────────────────────────────


def _capture(monkeypatch):
    captured = {}
    def fake_send(to, subj, html, text, force=False):
        captured.update(to=to, subj=subj, html=html, text=text, force=force)
        return True
    monkeypatch.setattr(email, "_send_email", fake_send)
    return captured


def test_digest_email_subject_singular_and_plural(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_match_digest_email(
        "a@b.com", "Lena Park", new_count=1,
        top_match_name="Marcus", top_match_title="VP", top_match_company="Acme",
        top_explanation="They are perfect.", magic_token="tok", force=True,
    )
    assert "1 new top match" in cap["subj"]
    assert "Lena," in cap["subj"]
    assert cap["force"] is True

    cap2 = _capture(monkeypatch)
    email.send_match_digest_email(
        "a@b.com", "Lena Park", new_count=5,
        top_match_name="Marcus", top_match_title="VP", top_match_company="Acme",
        top_explanation="They are perfect.", magic_token="tok", force=True,
    )
    assert "5 new top matches" in cap2["subj"]


def test_digest_email_features_top_match(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_match_digest_email(
        "a@b.com", "Lena", new_count=4,
        top_match_name="Marcus Chen", top_match_title="Head of Custody",
        top_match_company="Genventures",
        top_explanation="They run the institutional desk that aligns with your fundraising goal.",
        magic_token="tok", force=True,
    )
    for needle in ("Marcus Chen", "Head of Custody", "Genventures",
                   "institutional desk"):
        assert needle in cap["html"], f"{needle} missing from HTML"
        assert needle in cap["text"], f"{needle} missing from text"


def test_digest_email_uses_magic_link_when_present(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_match_digest_email(
        "a@b.com", "Lena", new_count=3,
        top_match_name="X", top_match_title="Y", top_match_company="Z",
        top_explanation="x", magic_token="tok123", force=True,
    )
    assert "/m/tok123" in cap["html"]


def test_digest_email_falls_back_to_matches_without_token(monkeypatch):
    cap = _capture(monkeypatch)
    email.send_match_digest_email(
        "a@b.com", "Lena", new_count=3,
        top_match_name="X", top_match_title="Y", top_match_company="Z",
        top_explanation="x", magic_token=None, force=True,
    )
    assert "/matches" in cap["html"]
    assert "/m/" not in cap["html"]


def test_digest_email_truncates_long_explanation(monkeypatch):
    cap = _capture(monkeypatch)
    long_exp = "a" * 500
    email.send_match_digest_email(
        "a@b.com", "Lena", new_count=3,
        top_match_name="X", top_match_title="Y", top_match_company="Z",
        top_explanation=long_exp, magic_token="t", force=True,
    )
    # ellipsis marker present, raw 500 a's not
    assert "…" in cap["html"]
    assert long_exp not in cap["html"]


# ── cron tests ───────────────────────────────────────────────────────────────


def _attendee(*, id=None, email_addr="x@y.com", name="Person", company="Co",
              title="Title", magic_access_token="t", email_opt_out=False,
              last_match_digest_at=None, privacy_mode="full"):
    return SimpleNamespace(
        id=id or uuid4(), email=email_addr, name=name, company=company,
        title=title, magic_access_token=magic_access_token,
        email_opt_out=email_opt_out, last_match_digest_at=last_match_digest_at,
        privacy_mode=privacy_mode,
    )


def _match_row(*, attendee_a_id, attendee_b_id, tier="curated",
               status_a="pending", status_b="pending", overall_score=0.85,
               explanation="x", created_at=None):
    if created_at is None:
        created_at = datetime(2026, 5, 28, 12, 0)
    return SimpleNamespace(
        attendee_a_id=attendee_a_id, attendee_b_id=attendee_b_id,
        tier=tier, status_a=status_a, status_b=status_b,
        overall_score=overall_score, explanation=explanation,
        created_at=created_at,
    )


def _mock_db(matches, attendees_by_id):
    """Build a mock AsyncSession that returns `matches` on the .execute call
    and lets `.get(Attendee, id)` look up `attendees_by_id`."""
    def _scalar_factory(items):
        scalars_obj = MagicMock()
        scalars_obj.all = MagicMock(return_value=items)
        r = MagicMock()
        r.scalars = MagicMock(return_value=scalars_obj)
        return r
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_factory(matches))
    db.get = AsyncMock(side_effect=lambda model, the_id: attendees_by_id.get(the_id))
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_threshold_three_fires_below_three_skips(monkeypatch):
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    b1, b2, b3 = (_attendee(name=f"B{i}", email_addr=f"b{i}@x.com") for i in range(3))
    # Three curated matches for Alice — meets threshold of 3.
    matches = [
        _match_row(attendee_a_id=a1.id, attendee_b_id=b.id)
        for b in (b1, b2, b3)
    ]
    db = _mock_db(matches, {a1.id: a1, b1.id: b1, b2.id: b2, b3.id: b3})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 1
    assert len(captured) == 1
    assert captured[0]["to_email"] == "alice@x.com"
    assert captured[0]["new_count"] == 3
    assert captured[0]["force"] is True


@pytest.mark.asyncio
async def test_two_matches_below_threshold_skipped(monkeypatch):
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    b1, b2 = _attendee(name="B1"), _attendee(name="B2")
    matches = [
        _match_row(attendee_a_id=a1.id, attendee_b_id=b1.id),
        _match_row(attendee_a_id=a1.id, attendee_b_id=b2.id),
    ]
    db = _mock_db(matches, {a1.id: a1, b1.id: b1, b2.id: b2})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 0
    assert res["skipped"] >= 1
    assert captured == []


@pytest.mark.asyncio
async def test_throttle_skips_recently_notified(monkeypatch):
    now = datetime(2026, 5, 29, 9, 0)
    recent = now - timedelta(hours=10)   # inside 72h window
    a1 = _attendee(name="Alice", email_addr="alice@x.com", last_match_digest_at=recent)
    bs = [_attendee(name=f"B{i}") for i in range(4)]
    matches = [_match_row(attendee_a_id=a1.id, attendee_b_id=b.id) for b in bs]
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3, throttle_hours=72, now=now)
    assert res["sent"] == 0
    assert res["skipped"] >= 1


@pytest.mark.asyncio
async def test_only_counts_matches_created_after_last_digest(monkeypatch):
    now = datetime(2026, 5, 29, 9, 0)
    last_digest = now - timedelta(hours=80)   # outside throttle, valid cutoff
    a1 = _attendee(name="Alice", email_addr="alice@x.com",
                   last_match_digest_at=last_digest)
    bs = [_attendee(name=f"B{i}") for i in range(5)]
    # 2 OLD (pre-last_digest) + 3 NEW (post-last_digest) — should fire on 3.
    old_ts = last_digest - timedelta(hours=5)
    new_ts = last_digest + timedelta(hours=5)
    matches = (
        [_match_row(attendee_a_id=a1.id, attendee_b_id=bs[i].id, created_at=old_ts)
         for i in range(2)]
        + [_match_row(attendee_a_id=a1.id, attendee_b_id=bs[i].id, created_at=new_ts)
           for i in range(2, 5)]
    )
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3, throttle_hours=72, now=now)
    assert res["sent"] == 1
    assert captured[0]["new_count"] == 3   # only the 3 new ones


@pytest.mark.asyncio
async def test_opt_out_attendees_skipped(monkeypatch):
    a1 = _attendee(name="Opt", email_addr="opt@x.com", email_opt_out=True)
    bs = [_attendee(name=f"B{i}") for i in range(3)]
    matches = [_match_row(attendee_a_id=a1.id, attendee_b_id=b.id) for b in bs]
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 0
    assert captured == []


@pytest.mark.asyncio
async def test_no_magic_token_skipped(monkeypatch):
    a1 = _attendee(name="Alice", email_addr="alice@x.com", magic_access_token=None)
    bs = [_attendee(name=f"B{i}") for i in range(3)]
    matches = [_match_row(attendee_a_id=a1.id, attendee_b_id=b.id) for b in bs]
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 0
    assert captured == []


@pytest.mark.asyncio
async def test_already_reviewed_matches_dont_count(monkeypatch):
    """If Alice already accepted/declined a curated match, that match should
    NOT count toward the digest threshold — she has already seen it."""
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    bs = [_attendee(name=f"B{i}") for i in range(4)]
    # 2 already-reviewed (a-side accepted) + 2 pending = only 2 new — below 3.
    matches = (
        [_match_row(attendee_a_id=a1.id, attendee_b_id=bs[i].id, status_a="accepted")
         for i in range(2)]
        + [_match_row(attendee_a_id=a1.id, attendee_b_id=bs[i].id)
           for i in range(2, 4)]
    )
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 0
    assert captured == []


@pytest.mark.asyncio
async def test_features_highest_score_match_in_digest(monkeypatch):
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    low = _attendee(name="LowScore", company="LowCo", title="Junior")
    mid = _attendee(name="MidScore", company="MidCo", title="Senior")
    high = _attendee(name="TopMatch", company="TopCo", title="CTO")
    matches = [
        _match_row(attendee_a_id=a1.id, attendee_b_id=low.id, overall_score=0.62, explanation="low"),
        _match_row(attendee_a_id=a1.id, attendee_b_id=mid.id, overall_score=0.74, explanation="mid"),
        _match_row(attendee_a_id=a1.id, attendee_b_id=high.id, overall_score=0.91, explanation="best"),
    ]
    db = _mock_db(matches, {a1.id: a1, low.id: low, mid.id: mid, high.id: high})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 1
    assert captured[0]["top_match_name"] == "TopMatch"
    assert captured[0]["top_match_company"] == "TopCo"
    assert captured[0]["top_explanation"] == "best"


@pytest.mark.asyncio
async def test_priority_intro_tier_counts(monkeypatch):
    """priority_intro tier matches should count just like curated."""
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    bs = [_attendee(name=f"B{i}") for i in range(3)]
    matches = [
        _match_row(attendee_a_id=a1.id, attendee_b_id=bs[i].id, tier="priority_intro")
        for i in range(3)
    ]
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 1
    assert captured[0]["new_count"] == 3


@pytest.mark.asyncio
async def test_b2b_only_top_match_uses_company_name(monkeypatch):
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    top = _attendee(name="Real Name", company="Elliptic", privacy_mode="b2b_only")
    others = [_attendee(name=f"B{i}") for i in range(2)]
    matches = (
        [_match_row(attendee_a_id=a1.id, attendee_b_id=top.id, overall_score=0.95)]
        + [_match_row(attendee_a_id=a1.id, attendee_b_id=o.id, overall_score=0.70)
           for o in others]
    )
    db = _mock_db(matches, {a1.id: a1, top.id: top, **{o.id: o for o in others}})

    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["sent"] == 1
    assert captured[0]["top_match_name"] == "Elliptic"
    assert captured[0]["top_match_title"] == ""
    assert "Real Name" not in str(captured[0])


@pytest.mark.asyncio
async def test_tz_aware_created_at_from_postgres_does_not_crash(monkeypatch):
    """Regression: Match.created_at comes back from Supabase with tz info
    (+00:00) even though the ORM column is `DateTime` not `DateTime(tz)`.
    Comparing it against a naive cutoff used to raise TypeError and the
    whole cron returned errors=N, sent=0. The _naive() helper strips tz
    on read so the comparison succeeds."""
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    bs = [_attendee(name=f"B{i}") for i in range(3)]
    tz_aware = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
    matches = [
        _match_row(attendee_a_id=a1.id, attendee_b_id=bs[i].id, created_at=tz_aware)
        for i in range(3)
    ]
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})
    captured = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3)
    assert res["errors"] == 0
    assert res["sent"] == 1


@pytest.mark.asyncio
async def test_max_sends_caps_run(monkeypatch):
    """A runaway scenario (cold-start, mass insert) must not blow through the
    domain's reputation budget. max_sends caps a single run."""
    recipients = [_attendee(name=f"A{i}", email_addr=f"a{i}@x.com") for i in range(10)]
    matches: list = []
    all_attendees: list = list(recipients)
    for a in recipients:
        bs = [_attendee(name=f"B{a.name}{i}") for i in range(3)]
        all_attendees.extend(bs)
        for b in bs:
            matches.append(_match_row(attendee_a_id=a.id, attendee_b_id=b.id))
    by_id = {x.id: x for x in all_attendees}
    db = _mock_db(matches, by_id)
    captured: list = []
    monkeypatch.setattr(mdc, "send_match_digest_email",
                        lambda **kw: (captured.append(kw), True)[1])
    res = await mdc.run_match_digest(db, threshold=3, max_sends=3)
    assert res["sent"] == 3
    assert len(captured) == 3


@pytest.mark.asyncio
async def test_throttle_stamp_set_on_successful_send(monkeypatch):
    a1 = _attendee(name="Alice", email_addr="alice@x.com")
    assert a1.last_match_digest_at is None
    bs = [_attendee(name=f"B{i}") for i in range(3)]
    matches = [_match_row(attendee_a_id=a1.id, attendee_b_id=b.id) for b in bs]
    db = _mock_db(matches, {a1.id: a1, **{b.id: b for b in bs}})
    monkeypatch.setattr(mdc, "send_match_digest_email", lambda **kw: True)
    now = datetime(2026, 5, 29, 9, 0)
    res = await mdc.run_match_digest(db, threshold=3, now=now)
    assert res["sent"] == 1
    assert a1.last_match_digest_at == now
