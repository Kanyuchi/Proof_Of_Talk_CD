"""TDD tests for app/services/interest_cron.py — reciprocity-loop cron.

Part A: run_interest_notifications
Part B: run_mutual_notifications

Uses AsyncMock fake-DB pattern (no test database), monkeypatches email sends.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _attendee(
    *,
    id=None,
    name="Test User",
    email="test@example.com",
    email_opt_out=False,
    magic_access_token="tok-abc123",
    last_interest_notified_at=None,
):
    return SimpleNamespace(
        id=id or uuid4(),
        name=name,
        email=email,
        email_opt_out=email_opt_out,
        magic_access_token=magic_access_token,
        last_interest_notified_at=last_interest_notified_at,
    )


def _match(
    *,
    id=None,
    attendee_a_id=None,
    attendee_b_id=None,
    status_a="pending",
    status_b="pending",
    status="pending",
    mutual_notified_at=None,
):
    return SimpleNamespace(
        id=id or uuid4(),
        attendee_a_id=attendee_a_id or uuid4(),
        attendee_b_id=attendee_b_id or uuid4(),
        status_a=status_a,
        status_b=status_b,
        status=status,
        mutual_notified_at=mutual_notified_at,
    )


def _make_db(rows_by_query=None):
    """Fake async DB that returns pre-baked rows per execute() call.

    rows_by_query: list of lists — each execute() call pops the next list
    from the front and returns it via .scalars().all().
    db.get() returns None by default; override per test.
    """
    queues = list(rows_by_query or [])
    call_idx = 0

    class _Scalars:
        def __init__(self, items): self._items = items
        def all(self): return self._items
        def first(self): return self._items[0] if self._items else None

    class _Result:
        def __init__(self, items): self._items = items
        def scalars(self): return _Scalars(self._items)

    db = AsyncMock()

    async def _execute(*a, **kw):
        nonlocal call_idx
        rows = queues[call_idx] if call_idx < len(queues) else []
        call_idx += 1
        return _Result(rows)

    db.execute = _execute
    db.commit = AsyncMock()
    db.get = AsyncMock(return_value=None)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# Part A — run_interest_notifications
# ─────────────────────────────────────────────────────────────────────────────

class TestRunInterestNotifications:
    """run_interest_notifications: incoming-pending counting, skips, sends."""

    @pytest.mark.asyncio
    async def test_counts_incoming_pending_for_b(self):
        """status_a=accepted, status_b=pending → attendee_b gets +1."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        # execute #1: pending-side matches; execute #2: attendees with those ids
        attendee_b = _attendee(id=aid_b)

        db = _make_db(rows_by_query=[[m]])
        # db.get for the attendee
        db.get = AsyncMock(side_effect=lambda model, aid: attendee_b if aid == aid_b else None)

        sent = []
        with patch("app.services.interest_cron.send_interest_notification",
                   side_effect=lambda **kw: sent.append(kw) or True):
            result = await run_interest_notifications(db)

        assert result["sent"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == 0
        assert sent[0]["to_email"] == "test@example.com"
        assert sent[0]["count"] == 1

    @pytest.mark.asyncio
    async def test_counts_incoming_pending_for_a(self):
        """status_b=accepted, status_a=pending → attendee_a gets +1."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_b="accepted", status_a="pending")
        attendee_a = _attendee(id=aid_a)

        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(side_effect=lambda model, aid: attendee_a if aid == aid_a else None)

        sent = []
        with patch("app.services.interest_cron.send_interest_notification",
                   side_effect=lambda **kw: sent.append(kw) or True):
            result = await run_interest_notifications(db)

        assert result["sent"] == 1
        assert sent[0]["count"] == 1

    @pytest.mark.asyncio
    async def test_aggregates_multiple_incomings(self):
        """Three matches all pending on B → B gets count=3."""
        from app.services.interest_cron import run_interest_notifications
        aid_a1, aid_a2, aid_a3, aid_b = uuid4(), uuid4(), uuid4(), uuid4()
        matches = [
            _match(attendee_a_id=aid_a1, attendee_b_id=aid_b, status_a="accepted", status_b="pending"),
            _match(attendee_a_id=aid_a2, attendee_b_id=aid_b, status_a="accepted", status_b="pending"),
            _match(attendee_a_id=aid_a3, attendee_b_id=aid_b, status_a="accepted", status_b="pending"),
        ]
        attendee_b = _attendee(id=aid_b)
        db = _make_db(rows_by_query=[matches])
        db.get = AsyncMock(side_effect=lambda model, aid: attendee_b if aid == aid_b else None)

        sent = []
        with patch("app.services.interest_cron.send_interest_notification",
                   side_effect=lambda **kw: sent.append(kw) or True):
            result = await run_interest_notifications(db)

        assert result["sent"] == 1
        assert sent[0]["count"] == 3

    @pytest.mark.asyncio
    async def test_skips_email_opt_out(self):
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        attendee = _attendee(id=aid_b, email_opt_out=True)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification") as mock_send:
            result = await run_interest_notifications(db)

        mock_send.assert_not_called()
        assert result["sent"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_no_email(self):
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        attendee = _attendee(id=aid_b, email=None)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification") as mock_send:
            result = await run_interest_notifications(db)

        mock_send.assert_not_called()
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_no_magic_token(self):
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        attendee = _attendee(id=aid_b, magic_access_token=None)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification") as mock_send:
            result = await run_interest_notifications(db)

        mock_send.assert_not_called()
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_demo_domain(self):
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        attendee = _attendee(id=aid_b, email="persona@demo.proofoftalk.io")
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification") as mock_send:
            result = await run_interest_notifications(db)

        mock_send.assert_not_called()
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_recently_notified(self):
        """last_interest_notified_at within 20h → throttled."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        recent_ts = datetime.utcnow() - timedelta(hours=5)
        attendee = _attendee(id=aid_b, last_interest_notified_at=recent_ts)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification") as mock_send:
            result = await run_interest_notifications(db)

        mock_send.assert_not_called()
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_sends_when_notified_more_than_20h_ago(self):
        """last_interest_notified_at > 20h ago → eligible, should send."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        old_ts = datetime.utcnow() - timedelta(hours=25)
        attendee = _attendee(id=aid_b, last_interest_notified_at=old_ts)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        sent = []
        with patch("app.services.interest_cron.send_interest_notification",
                   side_effect=lambda **kw: sent.append(kw) or True):
            result = await run_interest_notifications(db)

        assert result["sent"] == 1
        assert len(sent) == 1

    @pytest.mark.asyncio
    async def test_stamps_last_interest_notified_at_on_success(self):
        """After successful send, last_interest_notified_at is set and commit called."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        attendee = _attendee(id=aid_b)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification", return_value=True):
            await run_interest_notifications(db)

        assert attendee.last_interest_notified_at is not None
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_does_not_stamp_on_send_failure(self):
        """If send returns False, last_interest_notified_at is NOT set."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending")
        attendee = _attendee(id=aid_b)
        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(return_value=attendee)

        with patch("app.services.interest_cron.send_interest_notification", return_value=False):
            result = await run_interest_notifications(db)

        assert attendee.last_interest_notified_at is None
        # counted as skipped (send returned False), not error
        assert result["sent"] == 0

    @pytest.mark.asyncio
    async def test_no_pending_matches_returns_zero_counts(self):
        """No pending-sided matches → nothing to do."""
        from app.services.interest_cron import run_interest_notifications
        # Two mutual matches, no pending sides
        aid_a, aid_b = uuid4(), uuid4()
        matches = [
            _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="accepted"),
        ]
        db = _make_db(rows_by_query=[matches])

        with patch("app.services.interest_cron.send_interest_notification") as mock_send:
            result = await run_interest_notifications(db)

        mock_send.assert_not_called()
        assert result["sent"] == 0
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_per_attendee_error_counted_not_raised(self):
        """An exception during a single attendee's send is caught; others proceed."""
        from app.services.interest_cron import run_interest_notifications
        aid_a, aid_b, aid_c = uuid4(), uuid4(), uuid4()
        aid_d = uuid4()
        matches = [
            _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status_a="accepted", status_b="pending"),
            _match(attendee_a_id=aid_c, attendee_b_id=aid_d, status_a="accepted", status_b="pending"),
        ]
        attendee_b = _attendee(id=aid_b)
        attendee_d = _attendee(id=aid_d)

        db = _make_db(rows_by_query=[matches])

        call_count = 0
        def _get(model, aid):
            if aid == aid_b:
                return attendee_b
            if aid == aid_d:
                return attendee_d
            return None

        db.get = AsyncMock(side_effect=_get)

        sends = []
        call_n = 0
        def _side(*a, **kw):
            nonlocal call_n
            call_n += 1
            if call_n == 1:
                raise RuntimeError("network timeout")
            sends.append(kw)
            return True

        with patch("app.services.interest_cron.send_interest_notification", side_effect=_side):
            result = await run_interest_notifications(db)

        # One error, one send
        assert result["errors"] == 1
        assert result["sent"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Part B — run_mutual_notifications
# ─────────────────────────────────────────────────────────────────────────────

class TestRunMutualNotifications:
    """run_mutual_notifications: un-notified mutual matches → emails to both parties."""

    @pytest.mark.asyncio
    async def test_picks_only_unnotified_mutuals(self):
        """status='accepted', mutual_notified_at=None → selected."""
        from app.services.interest_cron import run_mutual_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status="accepted", mutual_notified_at=None)

        att_a = _attendee(id=aid_a, name="Alice", email="alice@x.com")
        att_b = _attendee(id=aid_b, name="Bob", email="bob@x.com")

        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(side_effect=lambda model, aid: att_a if aid == aid_a else att_b)

        sent_to = []
        with patch("app.services.interest_cron.send_mutual_match_email",
                   side_effect=lambda **kw: sent_to.append(kw.get("to_email")) or True):
            result = await run_mutual_notifications(db)

        assert result["sent"] == 2           # both parties
        assert result["errors"] == 0
        assert set(sent_to) == {"alice@x.com", "bob@x.com"}

    @pytest.mark.asyncio
    async def test_stamps_mutual_notified_at(self):
        """match.mutual_notified_at is set after emails go out."""
        from app.services.interest_cron import run_mutual_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status="accepted", mutual_notified_at=None)
        att_a = _attendee(id=aid_a, email="alice@x.com")
        att_b = _attendee(id=aid_b, email="bob@x.com")

        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(side_effect=lambda model, aid: att_a if aid == aid_a else att_b)

        with patch("app.services.interest_cron.send_mutual_match_email", return_value=True):
            await run_mutual_notifications(db)

        assert m.mutual_notified_at is not None
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_skips_already_notified_mutuals(self):
        """mutual_notified_at already set → not selected."""
        from app.services.interest_cron import run_mutual_notifications
        # The query itself filters mutual_notified_at IS NULL, so we return []
        db = _make_db(rows_by_query=[[]])   # empty result set

        with patch("app.services.interest_cron.send_mutual_match_email") as mock_send:
            result = await run_mutual_notifications(db)

        mock_send.assert_not_called()
        assert result["sent"] == 0

    @pytest.mark.asyncio
    async def test_does_not_resend_on_rerun(self):
        """Idempotency: run once, mutual_notified_at is set, second run sees empty list."""
        from app.services.interest_cron import run_mutual_notifications

        # First run: one un-notified match
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status="accepted", mutual_notified_at=None)
        att_a = _attendee(id=aid_a, email="a@x.com")
        att_b = _attendee(id=aid_b, email="b@x.com")

        db1 = _make_db(rows_by_query=[[m]])
        db1.get = AsyncMock(side_effect=lambda model, aid: att_a if aid == aid_a else att_b)

        with patch("app.services.interest_cron.send_mutual_match_email", return_value=True):
            r1 = await run_mutual_notifications(db1)

        assert r1["sent"] == 2
        assert m.mutual_notified_at is not None

        # Second run: match now has mutual_notified_at set — simulate DB returning []
        db2 = _make_db(rows_by_query=[[]])
        with patch("app.services.interest_cron.send_mutual_match_email") as mock_send2:
            r2 = await run_mutual_notifications(db2)

        mock_send2.assert_not_called()
        assert r2["sent"] == 0

    @pytest.mark.asyncio
    async def test_respects_opt_out_per_party(self):
        """One party has email_opt_out=True → only other party gets email; match still stamped."""
        from app.services.interest_cron import run_mutual_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status="accepted", mutual_notified_at=None)
        att_a = _attendee(id=aid_a, email="a@x.com", email_opt_out=True)
        att_b = _attendee(id=aid_b, email="b@x.com", email_opt_out=False)

        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(side_effect=lambda model, aid: att_a if aid == aid_a else att_b)

        sent_to = []
        with patch("app.services.interest_cron.send_mutual_match_email",
                   side_effect=lambda **kw: sent_to.append(kw.get("to_email")) or True):
            result = await run_mutual_notifications(db)

        assert sent_to == ["b@x.com"]   # only the non-opted-out party
        assert result["sent"] == 1
        # match is still stamped even though one side was skipped
        assert m.mutual_notified_at is not None

    @pytest.mark.asyncio
    async def test_respects_no_email_per_party(self):
        """One party has no email → only other party gets email."""
        from app.services.interest_cron import run_mutual_notifications
        aid_a, aid_b = uuid4(), uuid4()
        m = _match(attendee_a_id=aid_a, attendee_b_id=aid_b, status="accepted", mutual_notified_at=None)
        att_a = _attendee(id=aid_a, email=None)
        att_b = _attendee(id=aid_b, email="b@x.com")

        db = _make_db(rows_by_query=[[m]])
        db.get = AsyncMock(side_effect=lambda model, aid: att_a if aid == aid_a else att_b)

        sent_to = []
        with patch("app.services.interest_cron.send_mutual_match_email",
                   side_effect=lambda **kw: sent_to.append(kw.get("to_email")) or True):
            result = await run_mutual_notifications(db)

        assert sent_to == ["b@x.com"]
        assert result["sent"] == 1

    @pytest.mark.asyncio
    async def test_per_match_error_counted_not_raised(self):
        """Exception during a match's processing is caught; others proceed."""
        from app.services.interest_cron import run_mutual_notifications
        aid_a1, aid_b1 = uuid4(), uuid4()
        aid_a2, aid_b2 = uuid4(), uuid4()
        m1 = _match(attendee_a_id=aid_a1, attendee_b_id=aid_b1, status="accepted", mutual_notified_at=None)
        m2 = _match(attendee_a_id=aid_a2, attendee_b_id=aid_b2, status="accepted", mutual_notified_at=None)

        att_a1 = _attendee(id=aid_a1, email="a1@x.com")
        att_b1 = _attendee(id=aid_b1, email="b1@x.com")
        att_a2 = _attendee(id=aid_a2, email="a2@x.com")
        att_b2 = _attendee(id=aid_b2, email="b2@x.com")

        db = _make_db(rows_by_query=[[m1, m2]])

        def _get(model, aid):
            return {aid_a1: att_a1, aid_b1: att_b1, aid_a2: att_a2, aid_b2: att_b2}.get(aid)

        db.get = AsyncMock(side_effect=_get)

        call_n = 0
        def _send(**kw):
            nonlocal call_n
            call_n += 1
            if call_n == 1:
                raise RuntimeError("smtp timeout")
            return True

        with patch("app.services.interest_cron.send_mutual_match_email", side_effect=_send):
            result = await run_mutual_notifications(db)

        assert result["errors"] >= 1
