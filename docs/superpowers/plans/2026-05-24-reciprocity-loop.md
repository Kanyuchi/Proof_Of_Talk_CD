# Reciprocity Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let no-login attendees accept a match back in one tap, and pull the ~135 dormant one-sided-accept targets back into the app, so one-sided accepts convert into mutual matches before the June 2–3 event.

**Architecture:** Add a tokenless `PATCH /m/{token}/status` endpoint (mirrors the existing magic-link defer endpoint) so the 82% with no account can close a mutual. Add a transactional "N people want to meet you" email and an operator backlog script (mirrors `send_welcome_batch.py`) to notify the existing dormant targets, throttled by a new `attendees.last_interest_notified_at` column. Surface the existing "Requests" pattern on the magic-link page, deep-linked from the email via `?tab=requests`. The recurring cron and un-gating the mutual-completion email are an explicit fast-follow, not this plan.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy async / Alembic / pytest (backend); React 18 / TypeScript / Vite / React Query (frontend); Resend (email); Supabase REST (operator script).

**Spec:** `docs/superpowers/specs/2026-05-24-reciprocity-loop-design.md`

---

## File Structure

- `backend/app/models/attendee.py` — add `last_interest_notified_at` column to `Attendee` (throttle marker).
- `backend/alembic/versions/<rev>_add_last_interest_notified_at.py` — migration for the new column.
- `backend/app/api/routes/matches.py` — add `MagicStatusRequest` schema + `PATCH /m/{token}/status` endpoint.
- `backend/app/services/email.py` — add `send_interest_notification(...)`.
- `backend/scripts/notify_pending_interest.py` — operator backlog blast (mirrors `send_welcome_batch.py`).
- `backend/tests/test_magic_status.py` — endpoint unit tests.
- `backend/tests/test_interest_notification.py` — email-builder unit tests.
- `backend/tests/test_notify_pending_interest.py` — script pure-function unit tests.
- `frontend/src/api/client.ts` — add `acceptMatchByMagicLink(...)`.
- `frontend/src/pages/MagicMatches.tsx` — add the Requests surface + accept/decline + `?tab=requests` deep-link.
- `frontend/src/pages/MyMatches.tsx` — honor `?tab=requests` deep-link (open the existing Requests tab).

---

## Task 1: Migration — `attendees.last_interest_notified_at`

**Files:**
- Modify: `backend/app/models/attendee.py` (after line 88, `last_seen_at`)
- Create: `backend/alembic/versions/<rev>_add_last_interest_notified_at.py`
- Test: `backend/tests/test_magic_status.py` (model attribute assertion lives here; created in Task 2 — for Task 1 add a tiny standalone check first)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_last_interest_column.py`:

```python
"""attendees.last_interest_notified_at exists and is nullable (reciprocity throttle)."""

def test_attendee_has_last_interest_notified_at():
    from app.models.attendee import Attendee
    cols = Attendee.__table__.columns
    assert "last_interest_notified_at" in cols
    assert cols["last_interest_notified_at"].nullable is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_last_interest_column.py -v`
Expected: FAIL — `assert "last_interest_notified_at" in cols` is False.

- [ ] **Step 3: Add the column to the model**

In `backend/app/models/attendee.py`, immediately after the `last_seen_at` line (88):

```python
    # When we last emailed this attendee "N people want to meet you" (reciprocity
    # pull-back throttle). NULL = never notified. Set by notify_pending_interest.py
    # and the future recurring cron; lets the cron skip people the backlog covered.
    last_interest_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_last_interest_column.py -v`
Expected: PASS.

- [ ] **Step 5: Create the migration**

First confirm the current head: `cd backend && source .venv/bin/activate && alembic heads`
(Expected current head: `c3d4e5f6a7b8`, the adoption-tracking migration. If `alembic heads` shows something else, use that as `down_revision`.)

Create `backend/alembic/versions/d4e5f6a7b8c9_add_last_interest_notified_at.py`:

```python
"""add attendees.last_interest_notified_at

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendees",
        sa.Column("last_interest_notified_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attendees", "last_interest_notified_at")
```

- [ ] **Step 6: Apply the migration locally**

Run: `cd backend && source .venv/bin/activate && alembic upgrade head`
Expected: `Running upgrade c3d4e5f6a7b8 -> d4e5f6a7b8c9, add attendees.last_interest_notified_at`.
NOTE: `DATABASE_URL` in `backend/.env` points at prod Supabase — this applies to prod. That is intentional and matches the repo playbook (migrations run before merge). If you must avoid touching prod during dev, comment the apply and run it as the first rollout step instead.

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/models/attendee.py alembic/versions/d4e5f6a7b8c9_add_last_interest_notified_at.py tests/test_last_interest_column.py
git commit -m "feat(reciprocity): add attendees.last_interest_notified_at column + migration"
```

---

## Task 2: Backend — tokenless accept-back (`PATCH /m/{token}/status`)

**Files:**
- Modify: `backend/app/api/routes/matches.py` (add schema near `MagicDeferRequest` line 205; add endpoint after the `defer_match_by_magic_link` block ending line 255)
- Test: `backend/tests/test_magic_status.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_magic_status.py`:

```python
"""PATCH /matches/m/{token}/status — tokenless accept/decline (reciprocity loop).

Calls the route function directly with fake DB objects, mirroring
tests/test_match_defer.py (no test database in this repo)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


def _fake_db(attendee, match):
    """1st execute() resolves the attendee by token (.scalars().first());
    db.get() returns the match."""
    class _Scalars:
        def first(self): return attendee
    class _Result:
        def scalars(self): return _Scalars()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.get = AsyncMock(return_value=match)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_magic_accept_sets_a_side_and_computes_mutual():
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_a, magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=aid_a, attendee_b_id=aid_b,
        status_a="pending", status_b="accepted", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        out = await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )
    assert match.status_a == "accepted"
    assert match.status == "accepted"   # both sides accepted -> mutual
    assert out == "ok"


@pytest.mark.asyncio
async def test_magic_accept_sets_b_side():
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_b, magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=aid_a, attendee_b_id=aid_b,
        status_a="accepted", status_b="pending", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )
    assert match.status_b == "accepted"
    assert match.status == "accepted"


@pytest.mark.asyncio
async def test_magic_decline_sets_reason():
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    aid_a, aid_b = uuid4(), uuid4()
    attendee = SimpleNamespace(id=aid_a, magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=aid_a, attendee_b_id=aid_b,
        status_a="pending", status_b="accepted", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with patch("app.api.routes.matches._build_match_response", AsyncMock(return_value="ok")):
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="declined", decline_reason="not relevant"),
            db,
        )
    assert match.status_a == "declined"
    assert match.status == "declined"
    assert match.decline_reason == "not relevant"


@pytest.mark.asyncio
async def test_magic_status_rejects_non_owner():
    from fastapi import HTTPException
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    attendee = SimpleNamespace(id=uuid4(), magic_access_token="tok-abcdef-1234567890")
    match = SimpleNamespace(
        id=uuid4(), attendee_a_id=uuid4(), attendee_b_id=uuid4(),
        status_a="pending", status_b="pending", status="pending", decline_reason=None,
    )
    db = _fake_db(attendee, match)
    with pytest.raises(HTTPException) as exc:
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=match.id, status="accepted"),
            db,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_magic_status_rejects_bad_status():
    from fastapi import HTTPException
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    attendee = SimpleNamespace(id=uuid4(), magic_access_token="tok-abcdef-1234567890")
    db = _fake_db(attendee, SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        await update_match_status_by_magic_link(
            "tok-abcdef-1234567890",
            MagicStatusRequest(match_id=uuid4(), status="met"),
            db,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_magic_status_rejects_short_token():
    from fastapi import HTTPException
    from app.api.routes.matches import update_match_status_by_magic_link, MagicStatusRequest
    with pytest.raises(HTTPException) as exc:
        await update_match_status_by_magic_link(
            "short", MagicStatusRequest(match_id=uuid4(), status="accepted"), AsyncMock(),
        )
    assert exc.value.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_magic_status.py -v`
Expected: FAIL — `ImportError: cannot import name 'update_match_status_by_magic_link'`.

- [ ] **Step 3: Add the schema + endpoint**

In `backend/app/api/routes/matches.py`, after the `MagicDeferRequest` class (line 205–206) add:

```python
class MagicStatusRequest(BaseModel):
    match_id: UUID
    status: str
    decline_reason: str | None = None
```

Then, immediately after the `defer_match_by_magic_link` function (ends line 255), add:

```python
@router.patch("/m/{token}/status", response_model=MatchResponse)
async def update_match_status_by_magic_link(
    token: str,
    data: MagicStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """Magic-link accept/decline — no login required. Sets ONLY the caller's own
    side and recomputes the mutual state, so a no-login attendee can accept an
    incoming request back in one tap. Sends no email inline: the request path
    stays force-clean; mutual/pull-back notifications run off the request path
    (notify_pending_interest.py + the future cron)."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")
    if data.status not in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="Status must be accepted or declined")
    result = await db.execute(select(Attendee).where(Attendee.magic_access_token == token))
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    match = await db.get(Match, data.match_id)
    if not match or attendee.id not in (match.attendee_a_id, match.attendee_b_id):
        raise HTTPException(status_code=404, detail="Match not found")
    if match.attendee_a_id == attendee.id:
        match.status_a = data.status
    else:
        match.status_b = data.status
    match.status = _compute_overall_status(match.status_a, match.status_b)
    if data.status == "declined":
        match.decline_reason = data.decline_reason
    await db.commit()
    await db.refresh(match)
    return await _build_match_response(db, match, attendee.id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_magic_status.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full backend suite (no regressions)**

Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: all green (the prior count was 193 — expect 193 + new tests).

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/api/routes/matches.py tests/test_magic_status.py
git commit -m "feat(reciprocity): tokenless accept-back endpoint PATCH /m/{token}/status"
```

---

## Task 3: Backend — `send_interest_notification` email

**Files:**
- Modify: `backend/app/services/email.py` (add after `send_welcome_email`, ends line 527)
- Test: `backend/tests/test_interest_notification.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_interest_notification.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_interest_notification.py -v`
Expected: FAIL — `AttributeError: module 'app.services.email' has no attribute 'send_interest_notification'`.

- [ ] **Step 3: Add the email builder**

In `backend/app/services/email.py`, after `send_welcome_email` (ends line 527):

```python
def send_interest_notification(
    to_email: str,
    attendee_name: str,
    count: int,
    magic_token: str | None = None,
    app_url: str | None = None,
    force: bool = False,
) -> bool:
    """"N people want to meet you" pull-back email. The CTA lands on the
    magic-link Requests tab so a no-login attendee can accept back in one tap.

    `force=True` is for the operator backlog batch (notify_pending_interest.py)
    and the future recurring cron — both off the request path. Never call with
    force=True from a request handler (see _send_email docstring).
    """
    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    first_name = attendee_name.split()[0] if attendee_name else attendee_name
    requests_url = (
        f"{app_url}/m/{magic_token}?tab=requests" if magic_token else f"{app_url}/matches"
    )
    noun = "person wants" if count == 1 else "people want"
    subject = f"{count} {noun} to meet you at Proof of Talk"
    body_html = _render_email(
        preheader=f"{count} {noun} to meet you. Accept to lock in the meeting.",
        eyebrow="Mutual interest",
        heading=f"{count} {noun} to meet you",
        body_html=(
            f"<tr><td style=\"padding:0 0 14px;\">Hi {first_name}, {count} {noun} to meet you at "
            f"Proof of Talk 2026. They have already said yes. Accept them back and you can book a "
            f"meeting in one tap, no login needed.</td></tr>"
        ),
        cta_label="See who wants to meet you",
        cta_url=requests_url,
        cta_color="#E76315",
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )
    body_text = (
        f"{count} {noun} to meet you at Proof of Talk 2026, {first_name}.\n\n"
        f"They have already said yes. Accept them back and book a meeting in one tap:\n"
        f"{requests_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    return _send_email(to_email, subject, body_html, body_text, force=force)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_interest_notification.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/email.py tests/test_interest_notification.py
git commit -m "feat(reciprocity): send_interest_notification pull-back email"
```

---

## Task 4: Backend — operator backlog script `notify_pending_interest.py`

**Files:**
- Create: `backend/scripts/notify_pending_interest.py`
- Test: `backend/tests/test_notify_pending_interest.py`

- [ ] **Step 1: Write the failing tests (pure functions)**

Create `backend/tests/test_notify_pending_interest.py`:

```python
"""Pure-function tests for the reciprocity backlog script."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import notify_pending_interest as npi  # noqa: E402


def test_compute_incoming_counts_pending_side():
    matches = [
        {"attendee_a_id": "A", "attendee_b_id": "B", "status_a": "pending", "status_b": "accepted"},
        {"attendee_a_id": "A", "attendee_b_id": "C", "status_a": "pending", "status_b": "accepted"},
        {"attendee_a_id": "D", "attendee_b_id": "A", "status_a": "accepted", "status_b": "pending"},
        {"attendee_a_id": "X", "attendee_b_id": "Y", "status_a": "accepted", "status_b": "accepted"},
    ]
    inc = npi._compute_incoming(matches)
    assert inc["A"] == 3          # B, C, and D all accepted A; A still pending
    assert "D" not in inc         # D accepted, waiting on A — not an incoming request
    assert "X" not in inc         # already mutual


def test_classify_excludes_demo_optout_notoken_and_no_incoming():
    attendees = [
        {"id": "A", "email": "a@x.com", "magic_access_token": "t", "email_opt_out": False},
        {"id": "B", "email": "b@demo.proofoftalk.io", "magic_access_token": "t", "email_opt_out": False},
        {"id": "C", "email": "c@x.com", "magic_access_token": "t", "email_opt_out": True},
        {"id": "D", "email": "d@x.com", "magic_access_token": None, "email_opt_out": False},
        {"id": "E", "email": "e@x.com", "magic_access_token": "t", "email_opt_out": False},
    ]
    incoming = {"A": 2, "B": 1, "C": 1, "D": 1}   # E has no incoming
    out = npi._classify(attendees, incoming, ledger=set())
    assert [a["id"] for a in out["eligible"]] == ["A"]
    assert out["eligible"][0]["_incoming"] == 2
    assert out["skipped"]["demo"] == 1
    assert out["skipped"]["opted_out"] == 1
    assert out["skipped"]["no_token"] == 1
    assert out["skipped"]["no_incoming"] == 1


def test_classify_respects_ledger():
    attendees = [{"id": "A", "email": "a@x.com", "magic_access_token": "t", "email_opt_out": False}]
    out = npi._classify(attendees, {"A": 1}, ledger={"a@x.com"})
    assert out["eligible"] == []
    assert out["skipped"]["already_sent"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_notify_pending_interest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'notify_pending_interest'`.

- [ ] **Step 3: Write the script**

Create `backend/scripts/notify_pending_interest.py`:

```python
"""Reciprocity backlog blast: "N people want to meet you".

Emails every attendee who has at least one INCOMING pending request (someone
accepted them, they have not responded) — the dormant demand that never closed
into a mutual because nobody pulled them back to the app. Mirrors the safety
model of send_welcome_batch.py.

SAFETY MODEL
------------
* Preview by default. Nothing sends unless you pass --confirm.
* Each send uses send_interest_notification(force=True) — bypasses EMAIL_MODE
  for this deliberate operator batch only (this is an operator script, NOT a
  request path, so force is allowed). EMAIL_MODE stays "allowlist".
* Ledger (exports/interest_notified.log) prevents double-sends across reruns.
* On each send, stamps attendees.last_interest_notified_at via REST PATCH so the
  future recurring cron skips people this backlog already covered.

EXCLUSIONS
----------
* no incoming pending request        (nothing to tell them)
* email_opt_out = true               (unsubscribed)
* @demo.proofoftalk.io               (video personas)
* no magic_access_token              (link would dead-end at the login wall)
* already in the ledger

USAGE
-----
    python scripts/notify_pending_interest.py --status        # counts only
    python scripts/notify_pending_interest.py --limit 50      # preview a wave
    python scripts/notify_pending_interest.py --limit 50 --confirm   # send
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.email import send_interest_notification  # noqa: E402
from app.core.config import get_settings  # noqa: E402

SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}

LEDGER = Path(__file__).resolve().parent.parent / "exports" / "interest_notified.log"


def _load_ledger() -> set[str]:
    if not LEDGER.exists():
        return set()
    return {
        ln.strip().split("\t")[0].lower()
        for ln in LEDGER.read_text().splitlines()
        if ln.strip()
    }


def _append_ledger(email: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as fh:
        fh.write(f"{email.lower()}\t{time.strftime('%Y-%m-%dT%H:%M:%S')}\n")


def _fetch_attendees() -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(
            f"{SUPA_URL}/rest/v1/attendees",
            headers=H,
            params={
                "select": "id,name,email,magic_access_token,email_opt_out",
                "order": "created_at.asc",
                "limit": 1000,
                "offset": offset,
            },
            timeout=120,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        offset += 1000
    return rows


def _fetch_matches() -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(
            f"{SUPA_URL}/rest/v1/matches",
            headers=H,
            params={
                "select": "attendee_a_id,attendee_b_id,status_a,status_b",
                "limit": 1000,
                "offset": offset,
            },
            timeout=120,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        offset += 1000
    return rows


def _compute_incoming(matches: list[dict]) -> dict[str, int]:
    """attendee_id -> number of pending incoming requests (other side accepted)."""
    counts: dict[str, int] = {}
    for m in matches:
        a, b = m.get("attendee_a_id"), m.get("attendee_b_id")
        sa, sb = m.get("status_a"), m.get("status_b")
        if sa == "pending" and sb == "accepted" and a:
            counts[a] = counts.get(a, 0) + 1
        if sb == "pending" and sa == "accepted" and b:
            counts[b] = counts.get(b, 0) + 1
    return counts


def _classify(attendees: list[dict], incoming: dict[str, int], ledger: set[str]) -> dict:
    eligible, skipped = [], {
        "no_incoming": 0, "opted_out": 0, "no_token": 0,
        "no_email": 0, "already_sent": 0, "demo": 0,
    }
    for a in attendees:
        email = (a.get("email") or "").strip()
        if not email:
            skipped["no_email"] += 1
            continue
        if email.lower().endswith("@demo.proofoftalk.io"):
            skipped["demo"] += 1
            continue
        if incoming.get(a.get("id"), 0) < 1:
            skipped["no_incoming"] += 1
            continue
        if email.lower() in ledger:
            skipped["already_sent"] += 1
            continue
        if a.get("email_opt_out"):
            skipped["opted_out"] += 1
            continue
        if not a.get("magic_access_token"):
            skipped["no_token"] += 1
            continue
        eligible.append({**a, "_incoming": incoming.get(a.get("id"), 0)})
    return {"eligible": eligible, "skipped": skipped}


def _stamp_notified(attendee_id: str) -> None:
    try:
        httpx.patch(
            f"{SUPA_URL}/rest/v1/attendees",
            headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"},
            params={"id": f"eq.{attendee_id}"},
            json={"last_interest_notified_at": datetime.utcnow().isoformat()},
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"    ! stamp failed for {attendee_id}: {exc}")


def _print_summary(total: int, c: dict) -> None:
    s = c["skipped"]
    print(f"  total attendees:        {total}")
    print(f"  eligible (not sent):    {len(c['eligible'])}")
    print(f"  skipped — no incoming:  {s['no_incoming']}")
    print(f"  skipped — opted out:    {s['opted_out']}")
    print(f"  skipped — no token:     {s['no_token']}")
    print(f"  skipped — demo:         {s['demo']}")
    print(f"  skipped — no email:     {s['no_email']}")
    print(f"  skipped — already sent: {s['already_sent']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=50, help="max sends this wave (default 50)")
    ap.add_argument("--confirm", action="store_true", help="actually send (default: preview)")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between sends")
    ap.add_argument("--status", action="store_true", help="print counts and exit")
    args = ap.parse_args()

    if not SUPA_URL or not SUPA_KEY:
        ap.error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env")

    attendees = _fetch_attendees()
    incoming = _compute_incoming(_fetch_matches())
    ledger = _load_ledger()
    classified = _classify(attendees, incoming, ledger)

    if args.status:
        print("Reciprocity-notify status:")
        _print_summary(len(attendees), classified)
        return

    targets = classified["eligible"][: args.limit]

    settings = get_settings()
    from_addr = settings.RESEND_FROM_EMAIL
    from_warn = "  <-- WARNING: cold domain, expect spam" if "proofoftalk.io" in from_addr else ""

    print("Reciprocity-notify plan:")
    _print_summary(len(attendees), classified)
    print(f"\n  FROM:        {from_addr}{from_warn}")
    print(f"  this wave:   {len(targets)} (limit {args.limit})")
    print(f"  mode:        {'SEND (force, bypasses EMAIL_MODE)' if args.confirm else 'PREVIEW (no send)'}\n")
    for a in targets[:10]:
        print(f"    -> {a['email']:<40} {a['_incoming']} incoming")
    if len(targets) > 10:
        print(f"    … and {len(targets) - 10} more")

    if not args.confirm:
        print("\nPreview only. Re-run with --confirm to send.")
        return

    print(f"\nSending {len(targets)} reciprocity emails…")
    sent = failed = 0
    for i, a in enumerate(targets, 1):
        ok = send_interest_notification(
            to_email=a["email"],
            attendee_name=a.get("name") or "",
            count=a["_incoming"],
            magic_token=a.get("magic_access_token"),
            force=True,
        )
        if ok:
            sent += 1
            _append_ledger(a["email"])
            _stamp_notified(a["id"])
            print(f"  [{i}/{len(targets)}] sent    {a['email']} ({a['_incoming']})")
        else:
            failed += 1
            print(f"  [{i}/{len(targets)}] FAILED  {a['email']}")
        if i < len(targets):
            time.sleep(args.delay)

    print(f"\nDone. sent={sent} failed={failed} ledger={LEDGER}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_notify_pending_interest.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Smoke the script in preview mode (reads prod, sends nothing)**

Run: `cd backend && source .venv/bin/activate && python scripts/notify_pending_interest.py --status`
Expected: prints counts; "eligible" should be in the ballpark of the ~135 dormant targets (minus opt-outs/demo/no-token). No sends.

- [ ] **Step 6: Commit**

```bash
cd backend
git add scripts/notify_pending_interest.py tests/test_notify_pending_interest.py
git commit -m "feat(reciprocity): notify_pending_interest.py backlog blast script"
```

---

## Task 5: Frontend — `acceptMatchByMagicLink`

**Files:**
- Modify: `frontend/src/api/client.ts` (after `deferMatchByMagicLink`, line 157)

- [ ] **Step 1: Add the client function**

In `frontend/src/api/client.ts`, after `deferMatchByMagicLink` (ends line 157):

```typescript
export async function acceptMatchByMagicLink(
  token: string,
  matchId: string,
  status: "accepted" | "declined",
  decline_reason?: string
): Promise<Match> {
  const { data } = await api.patch(`/matches/m/${token}/status`, {
    match_id: matchId,
    status,
    decline_reason,
  });
  return data;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/api/client.ts
git commit -m "feat(reciprocity): acceptMatchByMagicLink client fn"
```

---

## Task 6: Frontend — Requests surface on MagicMatches + deep-link

**Files:**
- Modify: `frontend/src/pages/MagicMatches.tsx`
- Modify: `frontend/src/pages/MyMatches.tsx` (honor `?tab=requests`)

- [ ] **Step 1: Wire the accept mutation + compute requests in MagicMatches**

In `frontend/src/pages/MagicMatches.tsx`:

(a) Add `acceptMatchByMagicLink` to the import on line 8:

```typescript
import { getMatchesByMagicLink, updateProfileViaMagicLink, claimAccount, deferMatchByMagicLink, uploadPhotoViaMagicLink, acceptMatchByMagicLink } from "../api/client";
```

(b) After the `deferMutation` block (ends line 67), add the accept mutation and the request computation:

```typescript
  const acceptMutation = useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: "accepted" | "declined" }) =>
      acceptMatchByMagicLink(token!, matchId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["magic-matches", token] });
    },
  });

  // Incoming reciprocity requests: the other party accepted, this viewer has
  // not responded. Mirrors MyMatches.tsx. `attendee` is the viewer profile.
  const requestMatches = (data?.matches ?? []).filter((m) => {
    if (!attendee) return false;
    const iAmA = m.attendee_a_id === attendee.id;
    const myStatus = iAmA ? m.status_a : m.status_b;
    const otherStatus = iAmA ? m.status_b : m.status_a;
    return otherStatus === "accepted" && myStatus === "pending";
  });
```

- [ ] **Step 2: Render the Requests banner**

In `frontend/src/pages/MagicMatches.tsx`, find where the matches list begins to render (the `data.matches.map(...)` block). Immediately above it, insert this banner so it appears first:

```tsx
      {requestMatches.length > 0 && (
        <div className="mb-6 rounded-xl border border-[#E76315]/40 bg-[#E76315]/10 p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#E76315] opacity-60"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-[#E76315]"></span>
            </span>
            <h3 className="text-base font-semibold text-white">
              {requestMatches.length} {requestMatches.length === 1 ? "person wants" : "people want"} to meet you
            </h3>
          </div>
          <p className="text-sm text-white/60 mb-4">Accept to lock in the match, then book a time.</p>
          <div className="space-y-3">
            {requestMatches.map((m) => (
              <div key={m.id} className="flex items-center justify-between gap-3 rounded-lg bg-black/20 p-3">
                <div className="flex items-center gap-3 min-w-0">
                  <AttendeeAvatar attendee={m.matched_attendee} size={40} />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-white truncate">
                      {m.matched_attendee?.name ?? "A fellow attendee"}
                    </div>
                    <div className="text-xs text-white/50 truncate">
                      {[m.matched_attendee?.title, m.matched_attendee?.company].filter(Boolean).join(" · ")}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => acceptMutation.mutate({ matchId: m.id, status: "accepted" })}
                    disabled={acceptMutation.isPending}
                    className="rounded-lg bg-[#E76315] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => acceptMutation.mutate({ matchId: m.id, status: "declined" })}
                    disabled={acceptMutation.isPending}
                    className="rounded-lg border border-white/15 px-3 py-2 text-xs font-medium text-white/70 disabled:opacity-50"
                  >
                    Not now
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
```

NOTE: if `AttendeeAvatar`'s prop name differs from `attendee`, match the signature already used elsewhere in this file (it is imported on line 12). If the matched attendee is privacy-redacted (no name), the fallback copy "A fellow attendee" covers it.

- [ ] **Step 3: Deep-link scroll on `?tab=requests`**

In `frontend/src/pages/MagicMatches.tsx`, `useSearchParams` is already imported (line 2) and `searchParams` already exists (line 28). Add a ref + effect near the existing `claimRef`/effect (lines 30–35):

```typescript
  const requestsRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (searchParams.get("tab") === "requests") {
      requestsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [searchParams, data]);
```

Wrap the Requests banner from Step 2 in `<div ref={requestsRef}>...</div>` so the scroll target exists.

- [ ] **Step 4: Typecheck + build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: clean build.

- [ ] **Step 5: Honor `?tab=requests` on the authenticated MyMatches page**

In `frontend/src/pages/MyMatches.tsx`, the page already has `activeTab` state (`"all" | "requests" | "saved"`). Make it initialize from the URL. Add the import if missing and set the initial state from the query param:

```typescript
import { useSearchParams } from "react-router-dom";
// ...inside the component, replacing the existing activeTab useState:
const [searchParams] = useSearchParams();
const [activeTab, setActiveTab] = useState<"all" | "requests" | "saved">(
  searchParams.get("tab") === "requests" ? "requests" : "all"
);
```

(If `useState` for `activeTab` already has a different default, preserve its type union; only change the initial value to honor `?tab=requests`.)

- [ ] **Step 6: Typecheck + build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: clean build.

- [ ] **Step 7: Commit**

```bash
cd frontend
git add src/pages/MagicMatches.tsx src/pages/MyMatches.tsx
git commit -m "feat(reciprocity): Requests surface + accept-back on magic-link page + ?tab=requests deep-link"
```

---

## Task 7: Browser E2E smoke (manual, no automated test)

- [ ] **Step 1: Verify the loop end-to-end against prod**

Using the demo personas (`<persona>@demo.proofoftalk.io` / `ProofDemo2026!`) or a test pair:
1. As account-holder A, accept a match with B (creates a one-sided request for B).
2. Open B's magic link with `?tab=requests`: `https://meet.proofoftalk.io/m/{B_token}?tab=requests`.
3. Confirm the "1 person wants to meet you" banner renders and scrolls into view.
4. Click **Accept** → confirm it becomes mutual (mutual UI / book-a-slot chip appears after refetch).
5. Confirm no console errors and the network PATCH returned 200.

Expected: the mutual closes from the no-login side in one tap. Record the result in `session_log.md`.

---

## Self-Review

**Spec coverage:**
- Tokenless accept-back (§Components 1) → Task 2 ✓ (+ client Task 5, UI Task 6)
- Requests UI on magic page + `?tab=requests` (§Components 2) → Task 6 ✓
- Pull-back notify email + backlog script (§Components 3) → Tasks 3 + 4 ✓
- Schema/throttle column (§Components 5) → Task 1 ✓
- Mutual completion email un-gated → explicitly fast-follow (spec §4), not in this plan ✓
- Recurring cron → explicitly fast-follow (spec §3), not in this plan ✓
- Deliverability (warm from-addr, ≤100/day waves, opt-out, ledger) → Task 4 script ✓

**Placeholder scan:** none — every code step has complete code. The only conditional instructions ("if AttendeeAvatar prop differs", "if activeTab default differs") are guardrails for matching existing local conventions, with a concrete default given.

**Type consistency:** `MagicStatusRequest{match_id,status,decline_reason}` is defined in Task 2 and consumed by `acceptMatchByMagicLink` (Task 5) and the UI (Task 6) with the same field names. `send_interest_notification(to_email, attendee_name, count, magic_token, app_url, force)` is defined in Task 3 and called identically in Task 4. `_compute_incoming` / `_classify` signatures match between the script (Task 4) and its tests.

---

## Rollout

1. Migration already applied to prod in Task 1 Step 6 (`DATABASE_URL`=prod). If you deferred it, run `alembic upgrade head` from a checkout that has the migration **before** merge.
2. Merge backend + frontend (feature branch → PR → squash, per repo convention). Railway + Netlify auto-deploy.
3. Verify deploy: `PATCH /api/v1/matches/m/{bad-token}/status` returns 400 (route exists), not 404; grep the live Netlify bundle for "people want to meet you".
4. Dry-run `python scripts/notify_pending_interest.py --status`; review the eligible count.
5. Send the first wave: `python scripts/notify_pending_interest.py --limit 100 --confirm` (≤100/day, warm `team@xventures.de`). Watch Resend deliverability.
6. Re-run daily until the backlog clears (the ledger prevents double-sends).
7. Watch mutual-match count climb on `/dashboard` (was 6) and booked meetings (was 1).
8. Fast-follow (separate plan): the recurring ~1–2h cron + un-gating the mutual-completion email off the request path.
