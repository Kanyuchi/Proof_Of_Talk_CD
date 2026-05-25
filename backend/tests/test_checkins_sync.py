"""Tests for checkins_sync — recovering per-attendee claimed-pass data from the
Extasy `checkins` report.

The check-ins feed is per-attendee (each claimed pass carries the real holder's
own email/name/company/title), unlike the buyer-keyed orders/tickets feed. These
tests pin the pass-type resolver (join to orders by order#+QR) and the
existing-wins upsert behaviour, mirroring the extasy_sync test approach (mocked
AsyncSession, no real DB).
"""

from collections import Counter
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.attendee import Attendee, TicketType
from app.services import checkins_sync


# ── fixtures / builders ──────────────────────────────────────────────────────

def _order(order_number: str, ticket_names: str, qr_codes: str) -> dict:
    """A minimal Extasy orders-report row."""
    return {"orderNumber": order_number, "ticketNames": ticket_names, "qrCodes": qr_codes}


def _checkin(email: str, order_number="O1", qr="qA", first="Real", last="Person",
             company="Acme Corp", title="CEO", country="FRA") -> dict:
    """A minimal Extasy checkins-report row (one claimed pass)."""
    return {
        "checkinId": "c-" + email,
        "displayableOrderNumber": order_number,
        "qrCode": qr,
        "firstName": first,
        "lastName": last,
        "email": email,
        "companyName": company,
        "jobTitle": title,
        "countryIso3Code": country,
        "phone": "",
        "city": "",
        "fullPrice": "0.00",
        "createdAt": "2026-05-01 10:00:00.000000",
    }


def _fake_db(existing=None):
    """Stand-in AsyncSession: begin_nested() is an async CM, execute() returns a
    result whose scalar_one_or_none() yields `existing`, add() captures rows."""
    db = MagicMock()

    @asynccontextmanager
    async def _nested():
        yield SimpleNamespace()

    db.begin_nested = _nested
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=existing)
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    db.added = []
    db.add = MagicMock(side_effect=lambda a: db.added.append(a))
    return db


# ── pass-type resolver ───────────────────────────────────────────────────────

def test_resolve_pass_qr_exact():
    op, os_ = checkins_sync._build_order_maps([_order("O1", "VIP Pass, General Pass", "qA, qB")])
    assert checkins_sync._resolve_pass(_checkin("a@x.io", "O1", "qA"), op, os_) == "VIP Pass"
    assert checkins_sync._resolve_pass(_checkin("a@x.io", "O1", "qB"), op, os_) == "General Pass"


def test_resolve_pass_single_type_order():
    """QR doesn't match but the order has exactly one distinct pass type."""
    op, os_ = checkins_sync._build_order_maps([_order("O2", "Speaker Pass, Speaker Pass", "qC, qD")])
    assert checkins_sync._resolve_pass(_checkin("a@x.io", "O2", "nomatch"), op, os_) == "Speaker Pass"


def test_resolve_pass_fallback_first_then_none():
    op, os_ = checkins_sync._build_order_maps([_order("O3", "VIP Pass, General Pass", "qE, qF")])
    # multi-type, no QR match -> first ticket on the order
    assert checkins_sync._resolve_pass(_checkin("a@x.io", "O3", "nope"), op, os_) == "VIP Pass"
    # unknown order -> None (caller maps to DELEGATE)
    assert checkins_sync._resolve_pass(_checkin("a@x.io", "O404", "x"), op, os_) is None


# ── upsert: new attendee ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_new_checkin_inserts_with_pass_company_title():
    op, os_ = checkins_sync._build_order_maps([_order("O1", "VIP Pass", "qA")])
    db = _fake_db(existing=None)
    stats = await checkins_sync._process_checkin_chunk(
        db, [_checkin("new@corp.io", "O1", "qA", company="Corp", title="Founder", country="USA")],
        op, os_, seen_emails=set(), inserted_ids=[], error_reasons=Counter(),
    )
    assert stats["inserted"] == 1
    (a,) = db.added
    assert a.email == "new@corp.io"
    assert a.company == "Corp"          # real per-attendee company, not domain-inferred
    assert a.title == "Founder"         # real job title (orders feed can't supply this)
    assert a.ticket_type == TicketType.VIP
    assert a.country_iso3 == "USA"
    assert a.enriched_profile["source"] == "checkin"
    assert a.enriched_profile["checkin"]["ticket_name"] == "VIP Pass"


@pytest.mark.asyncio
async def test_new_checkin_gets_magic_token():
    """New people must get a magic_access_token on insert so the welcome email's
    link works immediately (else they sit in the welcome 'no token' bucket until
    a separate backfill runs)."""
    op, os_ = checkins_sync._build_order_maps([_order("O1", "General Pass", "qA")])
    db = _fake_db(existing=None)
    await checkins_sync._process_checkin_chunk(
        db, [_checkin("tok@corp.io", "O1", "qA")], op, os_, set(), [], Counter())
    (a,) = db.added
    assert a.magic_access_token and len(a.magic_access_token) >= 20


@pytest.mark.asyncio
async def test_new_checkin_unknown_order_defaults_delegate():
    op, os_ = checkins_sync._build_order_maps([_order("O1", "VIP Pass", "qA")])
    db = _fake_db(existing=None)
    await checkins_sync._process_checkin_chunk(
        db, [_checkin("x@corp.io", order_number="UNKNOWN", qr="zz")],
        op, os_, set(), [], Counter(),
    )
    (a,) = db.added
    assert a.ticket_type == TicketType.DELEGATE


# ── upsert: existing attendee (existing-wins) ────────────────────────────────

@pytest.mark.asyncio
async def test_existing_backfills_blank_title_keeps_company():
    existing = Attendee(name="X", email="known@corp.io", company="RealCo", title="",
                        ticket_type=TicketType.DELEGATE, interests=[], enriched_profile={})
    op, os_ = checkins_sync._build_order_maps([_order("O1", "General Pass", "qA")])
    db = _fake_db(existing=existing)
    stats = await checkins_sync._process_checkin_chunk(
        db, [_checkin("known@corp.io", "O1", "qA", company="WrongCo", title="VP Eng")],
        op, os_, set(), [], Counter(),
    )
    assert existing.title == "VP Eng"     # blank filled from richer feed
    assert existing.company == "RealCo"   # populated value NOT overwritten
    assert db.added == []                 # no insert
    assert stats["backfilled"] == 1
    assert existing.enriched_profile["checkin"]["ticket_name"] == "General Pass"


@pytest.mark.asyncio
async def test_tier_upgrade_only_upward():
    existing = Attendee(name="X", email="k@corp.io", company="C", title="T",
                        ticket_type=TicketType.DELEGATE, interests=[], enriched_profile={})
    op, os_ = checkins_sync._build_order_maps([_order("O1", "VIP Pass", "qA")])
    db = _fake_db(existing=existing)
    stats = await checkins_sync._process_checkin_chunk(
        db, [_checkin("k@corp.io", "O1", "qA")], op, os_, set(), [], Counter())
    assert existing.ticket_type == TicketType.VIP
    assert stats["upgraded"] == 1


@pytest.mark.asyncio
async def test_tier_no_downgrade():
    existing = Attendee(name="X", email="k@corp.io", company="C", title="T",
                        ticket_type=TicketType.VIP, interests=[], enriched_profile={})
    op, os_ = checkins_sync._build_order_maps([_order("O1", "General Pass", "qA")])
    db = _fake_db(existing=existing)
    await checkins_sync._process_checkin_chunk(
        db, [_checkin("k@corp.io", "O1", "qA")], op, os_, set(), [], Counter())
    assert existing.ticket_type == TicketType.VIP   # delegate check-in does not downgrade


# ── skips ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_skips_test_name_duplicate_and_blank_email():
    op, os_ = checkins_sync._build_order_maps([_order("O1", "General Pass", "qA")])
    db = _fake_db(existing=None)
    seen: set = set()
    chunk = [
        _checkin("dup@corp.io", "O1", "qA"),
        _checkin("dup@corp.io", "O1", "qA"),                        # duplicate email -> skip
        _checkin("qa@corp.io", "O1", "qA", first="Test", last="User"),  # test/QA name -> skip
        _checkin("", "O1", "qA"),                                   # blank email -> skip
    ]
    stats = await checkins_sync._process_checkin_chunk(db, chunk, op, os_, seen, [], Counter())
    assert stats["inserted"] == 1
    assert [a.email for a in db.added] == ["dup@corp.io"]
