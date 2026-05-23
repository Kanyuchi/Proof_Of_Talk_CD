# Adoption & Usage Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface accounts-created + signup trend, start recording real usage (password logins *and* magic-link opens) via throttled best-effort timestamps, snapshot per-day usage into a tiny `usage_daily` table via a daily cron, and render an admin-only "Adoption & Usage" card anchored to a tracking-start date.

**Architecture:** Two nullable timestamp columns (`users.last_login_at`, `attendees.last_seen_at`) capture "most recent activity"; throttled best-effort write hooks in `POST /auth/login` and `GET /matches/m/{token}` stamp them (only when NULL or >1h old, wrapped so a failure never breaks the response). A daily APScheduler job computes one idempotent `usage_daily` row (active_today / cumulative_active / account counts) and writes a `sync_status` heartbeat like every other cron. A new admin-gated `GET /dashboard/adoption` returns accounts metrics + historical `signups_by_day` (from `users.created_at`) + live usage counts + `usage_by_day` (from `usage_daily`). The frontend adds one React Query card mirroring the existing Sync Health / Weekly Growth panels.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async (Mapped/mapped_column), Alembic, APScheduler, pytest + pytest-asyncio (mock-based route tests, no test DB), React 18 + TypeScript + Vite + Tailwind, React Query (`@tanstack/react-query`), axios.

**Spec:** `docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md`

**Test convention (house style — follow exactly):** This repo has **no test database**. Route handlers are tested by either (a) calling the *undecorated coroutine* (`module.handler.__wrapped__(...)` when a `@limiter.limit` decorator is present — e.g. `POST /login`; call the function directly when no limiter) with an `AsyncMock()` db + a `_ScalarResult` helper for `.scalars().first()`, sequencing multiple queries with `db.execute.side_effect = [...]`; or (b) `TestClient(app, raise_server_exceptions=False)` + `app.dependency_overrides` with a fake `get_db` (see `tests/test_magic_matches_viewer.py`, `tests/test_pending_count_route.py`, `tests/test_auth_forgot_password.py`). Service functions that open their own `async_session()` are tested by patching the module's `async_session` with an async-context-manager mock (see `tests/test_profile_pipeline.py`). Patch external work and `asyncio.create_task`.

**Run tests:** `cd backend && source .venv/bin/activate && pytest <path> -v`

**Datetime convention:** the codebase uses naive `datetime.utcnow()` everywhere (`User.created_at`, `Match.*`, `grid_audit_run.run_at`, deferral stamps). **Match it** — use `datetime.utcnow()` for the timestamp columns and the throttle comparison. The cron's snapshot `day` is `datetime.utcnow().date()`.

---

## File Structure

| File | Create / Modify | Responsibility |
|---|---|---|
| `backend/alembic/versions/c3d4e5f6a7b8_add_usage_tracking.py` | Create | Migration: add `users.last_login_at` (TIMESTAMP NULL), `attendees.last_seen_at` (TIMESTAMP NULL), create `usage_daily` table. `down_revision = "b2c3d4e5f6a7"` (current head). |
| `backend/app/models/user.py` | Modify | Add `last_login_at: Mapped[datetime \| None]`. |
| `backend/app/models/attendee.py` | Modify | Add `last_seen_at: Mapped[datetime \| None]` to `Attendee`. |
| `backend/app/models/usage_daily.py` | Create | New `UsageDaily` ORM model (one row/day). |
| `backend/alembic/env.py` | Modify | Import `UsageDaily` so Base.metadata registers it. |
| `backend/app/api/routes/auth.py` | Modify | Throttled best-effort `last_login_at` write in `login` (~line 263–271). |
| `backend/app/api/routes/matches.py` | Modify | Throttled best-effort `last_seen_at` write in `get_matches_by_magic_link` (~line 154–188). |
| `backend/app/services/usage_snapshot.py` | Create | `compute_and_upsert_usage_daily(db)` — compute the day's row + idempotent upsert; pure-ish, takes a session. |
| `backend/app/main.py` | Modify | Register `_daily_usage_snapshot` cron (03:45 UTC) via `_run_with_heartbeat`; update lifespan log line. |
| `backend/app/api/routes/dashboard.py` | Modify | New admin-gated `GET /dashboard/adoption`. |
| `backend/tests/test_login_last_login.py` | Create | Throttle + best-effort tests for the login hook. |
| `backend/tests/test_magic_last_seen.py` | Create | Throttle + best-effort + "hook failure doesn't break response" tests for the magic-link hook. |
| `backend/tests/test_usage_snapshot.py` | Create | Snapshot compute correctness + idempotent re-run. |
| `backend/tests/test_adoption_endpoint.py` | Create | Admin-gating, JSON shape, real-vs-demo exclusion, pct math. |
| `frontend/src/api/client.ts` | Modify | `getAdoption()` GET `/dashboard/adoption` + return type. |
| `frontend/src/types/index.ts` | Modify | `Adoption` interface. |
| `frontend/src/hooks/useDashboard.ts` | Modify | `useAdoption()` React Query hook. |
| `frontend/src/pages/Dashboard.tsx` | Modify | "Adoption & Usage" card + empty/explainer state. |

**Column / key contract (must match across all tasks):**

- `users.last_login_at` — TIMESTAMP NULL
- `attendees.last_seen_at` — TIMESTAMP NULL
- `usage_daily` columns: `day DATE PK`, `total_accounts INT`, `real_accounts INT`, `active_today INT`, `cumulative_active INT`
- Endpoint JSON keys: `tracking_started_at`, `accounts{total,real,linked_to_attendee,pct_of_directory,directory_size}`, `signups_by_day[{day,n}]`, `usage{cumulative_active,active_last_7d,magic_link_active,login_active}`, `usage_by_day[{day,active_today,cumulative_active}]`
- Frontend TS `Adoption` mirrors the above exactly.
- "**real**" account = NOT `is_admin` AND email does NOT end with `@demo.proofoftalk.io` (mirrors `staff_filter`/`concierge._is_demo`). The `usage_daily.real_accounts` snapshot uses the same rule.

---

### Task 1: Alembic migration — two columns + `usage_daily` table

**Files:**
- Create: `backend/alembic/versions/c3d4e5f6a7b8_add_usage_tracking.py`
- Modify: `backend/alembic/env.py` (line 13–16 model-import block)

> No test-DB exists, so this task's "smoke test" is `python -c "import"` of the migration module + a structural assertion. Do NOT run `alembic upgrade` (constraint: do not touch the DB).

- [ ] **Step 1: Write the failing structural check**

```bash
cd backend && source .venv/bin/activate && \
python -c "
import importlib.util, pathlib
p = pathlib.Path('alembic/versions/c3d4e5f6a7b8_add_usage_tracking.py')
spec = importlib.util.spec_from_file_location('m', p)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.revision == 'c3d4e5f6a7b8'
assert m.down_revision == 'b2c3d4e5f6a7'
assert callable(m.upgrade) and callable(m.downgrade)
print('OK')
"
```
Expected: **FAIL** — `FileNotFoundError: alembic/versions/c3d4e5f6a7b8_add_usage_tracking.py`.

- [ ] **Step 2: Create the migration (complete code)**

```python
# backend/alembic/versions/c3d4e5f6a7b8_add_usage_tracking.py
"""add usage tracking — last_login_at, last_seen_at, usage_daily

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-24 12:00:00.000000

Adoption & Usage tracking: two nullable "most recent activity" timestamps
plus a tiny per-day snapshot table. See
docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    op.add_column("attendees", sa.Column("last_seen_at", sa.DateTime(), nullable=True))
    op.create_table(
        "usage_daily",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("total_accounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("real_accounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cumulative_active", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("usage_daily")
    op.drop_column("attendees", "last_seen_at")
    op.drop_column("users", "last_login_at")
```

- [ ] **Step 3: Register the new model in alembic env.py**

In `backend/alembic/env.py`, after the existing model imports (currently ends at line 16 with `from app.models.grid_audit_run import GridAuditRun  # noqa: F401`), add:

```python
from app.models.usage_daily import UsageDaily  # noqa: F401
```

(The `UsageDaily` model itself is created in Task 2; this import line will fail to import until then. Order Task 2 immediately after, or temporarily comment the import. Cleanest: do Step 3 *after* Task 2 Step 2. Defer Step 3 to the end of Task 2.)

- [ ] **Step 4: Run the structural check** — Expected: **PASS** (prints `OK`).

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/c3d4e5f6a7b8_add_usage_tracking.py
git commit -m "feat: add usage-tracking migration (last_login_at, last_seen_at, usage_daily)"
```

---

### Task 2: ORM models — two columns + `UsageDaily`

**Files:**
- Modify: `backend/app/models/user.py` (after line 21)
- Modify: `backend/app/models/attendee.py` (inside `Attendee`, after line 84 `email_opt_out`)
- Create: `backend/app/models/usage_daily.py`
- Modify: `backend/alembic/env.py` (the deferred import from Task 1 Step 3)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_models.py
from datetime import date, datetime

from app.models.user import User
from app.models.attendee import Attendee
from app.models.usage_daily import UsageDaily


def test_user_has_last_login_at_column():
    assert "last_login_at" in User.__table__.columns
    assert User.__table__.columns["last_login_at"].nullable is True


def test_attendee_has_last_seen_at_column():
    assert "last_seen_at" in Attendee.__table__.columns
    assert Attendee.__table__.columns["last_seen_at"].nullable is True


def test_usage_daily_columns_and_pk():
    cols = UsageDaily.__table__.columns
    assert set(c.name for c in cols) == {
        "day", "total_accounts", "real_accounts", "active_today", "cumulative_active",
    }
    assert UsageDaily.__table__.primary_key.columns.keys() == ["day"]


def test_usage_daily_instantiable():
    row = UsageDaily(
        day=date(2026, 5, 24),
        total_accounts=162, real_accounts=154, active_today=0, cumulative_active=0,
    )
    assert row.real_accounts == 154

    # the two timestamp columns accept a datetime
    u = User(email="x@y.z", hashed_password="h", full_name="X", last_login_at=datetime.utcnow())
    assert u.last_login_at is not None
```

- [ ] **Step 2: Run it** — `pytest tests/test_usage_models.py -v`. Expected: **FAIL** — `ModuleNotFoundError: No module named 'app.models.usage_daily'`.

- [ ] **Step 3: Create the model (complete code)**

```python
# backend/app/models/usage_daily.py
from datetime import date
from sqlalchemy import Date, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class UsageDaily(Base):
    """One snapshot row per UTC day, written by the daily usage cron. Captures
    the per-day history that overwriting last_login_at/last_seen_at would lose.
    See docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md.
    """
    __tablename__ = "usage_daily"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    total_accounts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    real_accounts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    active_today: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cumulative_active: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
```

- [ ] **Step 4: Add `last_login_at` to User** — in `backend/app/models/user.py`, after line 21 (`attendee_id`), add:

```python
    # Adoption tracking — set (throttled, best-effort) on successful password login
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

(`datetime` and `DateTime` are already imported at the top of `user.py`.)

- [ ] **Step 5: Add `last_seen_at` to Attendee** — in `backend/app/models/attendee.py`, after line 84 (`email_opt_out`), add:

```python
    # Adoption tracking — set (throttled, best-effort) on magic-link match view.
    # This is the hook that captures the magic-link majority (no-account users).
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

(`datetime` and `DateTime` are already imported at the top of `attendee.py`.)

- [ ] **Step 6: Register the model in alembic env.py** (Task 1 Step 3, deferred) — in `backend/app/alembic/env.py` after line 16:

```python
from app.models.usage_daily import UsageDaily  # noqa: F401
```

(Path is `backend/alembic/env.py`.)

- [ ] **Step 7: Run the test** — `pytest tests/test_usage_models.py -v`. Expected: **PASS** (4 passed).

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/usage_daily.py backend/app/models/user.py backend/app/models/attendee.py backend/alembic/env.py backend/tests/test_usage_models.py
git commit -m "feat: add UsageDaily model + last_login_at/last_seen_at columns"
```

---

### Task 3: Throttled best-effort `last_login_at` write in `POST /auth/login`

**Files:**
- Modify: `backend/app/api/routes/auth.py` (login handler, lines 263–271)
- Test: `backend/tests/test_login_last_login.py`

Throttle rule: write only if `last_login_at` is NULL or older than 1 hour. Best-effort: wrap in try/except so a write failure never blocks the token response.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_login_last_login.py
"""POST /auth/login stamps users.last_login_at (throttled, best-effort)."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.api.routes.auth as auth


class _ScalarResult:
    def __init__(self, row):
        self._row = row

    def scalars(self):
        return self

    def first(self):
        return self._row


async def _call_login(db, user):
    """Invoke the undecorated coroutine (bypasses the slowapi limiter)."""
    data = SimpleNamespace(email=user.email, password="pw")
    with patch.object(auth, "verify_password", MagicMock(return_value=True)), \
         patch.object(auth, "create_access_token", MagicMock(return_value="jwt")):
        return await auth.login.__wrapped__(SimpleNamespace(), data, db)


@pytest.mark.asyncio
async def test_login_stamps_last_login_when_null():
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=None,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    out = await _call_login(db, user)
    assert out.access_token == "jwt"
    assert user.last_login_at is not None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_login_throttles_recent_last_login():
    recent = datetime.utcnow() - timedelta(minutes=10)
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=recent,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    await _call_login(db, user)
    # unchanged — inside the 1h throttle window, so no rewrite and no commit
    assert user.last_login_at == recent
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_rewrites_when_older_than_1h():
    old = datetime.utcnow() - timedelta(hours=2)
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=old,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    await _call_login(db, user)
    assert user.last_login_at > old
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_login_hook_failure_does_not_break_response():
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=None,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    db.commit.side_effect = RuntimeError("db down")
    out = await _call_login(db, user)  # must NOT raise
    assert out.access_token == "jwt"


@pytest.mark.asyncio
async def test_login_bad_password_still_401_and_no_stamp():
    user = SimpleNamespace(
        id="u-1", email="a@b.com", hashed_password="h", last_login_at=None,
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(user)
    data = SimpleNamespace(email="a@b.com", password="wrong")
    from fastapi import HTTPException
    with patch.object(auth, "verify_password", MagicMock(return_value=False)):
        with pytest.raises(HTTPException) as ei:
            await auth.login.__wrapped__(SimpleNamespace(), data, db)
    assert ei.value.status_code == 401
    assert user.last_login_at is None
```

- [ ] **Step 2: Run it** — `pytest tests/test_login_last_login.py -v`. Expected: **FAIL** — the stamp/throttle assertions fail (handler doesn't touch `last_login_at` yet).

- [ ] **Step 3: Implement (complete code)** — replace the `login` handler body in `backend/app/api/routes/auth.py` (lines 263–271):

```python
@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password, returns JWT token."""
    user = (await db.execute(select(User).where(User.email == data.email))).scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Adoption tracking — stamp last_login_at, throttled to once/hour and
    # best-effort so a write failure never blocks the login response.
    try:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        if user.last_login_at is None or (now - user.last_login_at) > timedelta(hours=1):
            user.last_login_at = now
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — never let tracking break auth
        logger.warning("login: last_login_at write failed: %s", exc)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)
```

(`logger` is already defined at `auth.py:21`.)

- [ ] **Step 4: Run the test** — `pytest tests/test_login_last_login.py -v`. Expected: **PASS** (5 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_login_last_login.py
git commit -m "feat: stamp users.last_login_at on login (throttled, best-effort)"
```

---

### Task 4: Throttled best-effort `last_seen_at` write in `GET /matches/m/{token}`

**Files:**
- Modify: `backend/app/api/routes/matches.py` (`get_matches_by_magic_link`, lines 154–188)
- Test: `backend/tests/test_magic_last_seen.py`

Same throttle (NULL or >1h) and best-effort wrapping. Critically: a hook failure must not break the match-list response (the magic-link view rendering takes priority).

- [ ] **Step 1: Write the failing test** (TestClient + dependency_overrides, mirrors `test_magic_matches_viewer.py`)

```python
# backend/tests/test_magic_last_seen.py
"""GET /matches/m/{token} stamps attendees.last_seen_at (throttled, best-effort).

Mirrors tests/test_magic_matches_viewer.py: TestClient + dependency_overrides
with a fake DB (no test database in this repo).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db

_client = TestClient(app, raise_server_exceptions=False)
_TOKEN = "tok-abcdef-1234567890"


def _make_attendee(**overrides):
    base = dict(
        id=uuid4(), name="Magic User", email="m@example.invalid",
        company="Acme", title="Founder", ticket_type="DELEGATE",
        interests=["defi"], goals="raising", target_companies="a16z",
        seeking=[], not_looking_for=[], preferred_geographies=[],
        deal_stage=None, photo_url=None, linkedin_url=None,
        twitter_handle=None, company_website=None, ai_summary=None,
        intent_tags=[], vertical_tags=[], deal_readiness_score=None,
        enriched_profile={}, privacy_mode="full",
        magic_access_token=_TOKEN, created_at=datetime(2026, 1, 1),
        last_seen_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _override(attendee, *, commit_raises=False, commits=None):
    """Fake DB: 1st execute() = attendee lookup (.scalars().first()),
    2nd = match lookup (.scalars().all() -> []). Records commit calls so the
    test can assert throttle behaviour."""
    class _Scalars:
        def first(self): return attendee
        def all(self): return []

    class _Result:
        def scalars(self): return _Scalars()

    class _FakeDB:
        async def execute(self, *a, **k): return _Result()
        async def commit(self):
            if commits is not None:
                commits.append(1)
            if commit_raises:
                raise RuntimeError("db down")

    async def _dep():
        yield _FakeDB()
    return _dep


def _get():
    return _client.get(f"/api/v1/matches/m/{_TOKEN}")


def test_magic_open_stamps_last_seen_when_null():
    a = _make_attendee(last_seen_at=None)
    commits = []
    app.dependency_overrides[get_db] = _override(a, commits=commits)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 200, r.text
    assert a.last_seen_at is not None
    assert len(commits) == 1


def test_magic_open_throttles_recent():
    recent = datetime.utcnow() - timedelta(minutes=5)
    a = _make_attendee(last_seen_at=recent)
    commits = []
    app.dependency_overrides[get_db] = _override(a, commits=commits)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 200, r.text
    assert a.last_seen_at == recent       # unchanged
    assert commits == []                  # no write inside throttle window


def test_magic_open_rewrites_when_old():
    old = datetime.utcnow() - timedelta(hours=3)
    a = _make_attendee(last_seen_at=old)
    app.dependency_overrides[get_db] = _override(a)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 200, r.text
    assert a.last_seen_at > old


def test_magic_open_hook_failure_does_not_break_response():
    a = _make_attendee(last_seen_at=None)
    app.dependency_overrides[get_db] = _override(a, commit_raises=True)
    try:
        r = _get()
    finally:
        app.dependency_overrides.pop(get_db, None)
    # The match list must still render even though the timestamp write failed.
    assert r.status_code == 200, r.text
    assert r.json()["attendee_id"] == str(a.id)
```

- [ ] **Step 2: Run it** — `pytest tests/test_magic_last_seen.py -v`. Expected: **FAIL** — `last_seen_at`/commit assertions fail (handler doesn't stamp yet).

- [ ] **Step 3: Implement (complete code)** — in `backend/app/api/routes/matches.py`, inside `get_matches_by_magic_link`, immediately after the `if not attendee:` 404 block (after line 168) and before the `match_result = ...` query, insert:

```python
    # Adoption tracking — stamp last_seen_at (the magic-link majority path),
    # throttled to once/hour and best-effort so it never breaks the match view.
    try:
        from datetime import timedelta
        now = datetime.utcnow()
        if attendee.last_seen_at is None or (now - attendee.last_seen_at) > timedelta(hours=1):
            attendee.last_seen_at = now
            await db.commit()
    except Exception:
        pass  # the match-list response takes priority over recording the timestamp
```

(`datetime` is already imported at `matches.py:4` — `from datetime import datetime`.)

- [ ] **Step 4: Run the test** — `pytest tests/test_magic_last_seen.py -v`. Expected: **PASS** (4 passed). Also re-run `pytest tests/test_magic_matches_viewer.py -v` to confirm no regression.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/matches.py backend/tests/test_magic_last_seen.py
git commit -m "feat: stamp attendees.last_seen_at on magic-link open (throttled, best-effort)"
```

---

### Task 5: `usage_snapshot` service — compute + idempotent upsert

**Files:**
- Create: `backend/app/services/usage_snapshot.py`
- Test: `backend/tests/test_usage_snapshot.py`

`compute_and_upsert_usage_daily(db)` computes one row for `datetime.utcnow().date()` and upserts it (PostgreSQL `ON CONFLICT (day) DO UPDATE`, idempotent). Definitions:

- `total_accounts` = `COUNT(users)`.
- `real_accounts` = `COUNT(users WHERE NOT is_admin AND email NOT ILIKE '%@demo.proofoftalk.io')`.
- `active_today` = distinct people active in the prior 24h = `COUNT(DISTINCT users WHERE last_login_at >= now-24h)` + `COUNT(DISTINCT attendees WHERE last_seen_at >= now-24h AND attendee not already counted via a linked user)`. To avoid double-counting a person who both logged in and opened a magic link, subtract the overlap: attendees whose `id` is in the set of recently-active users' `attendee_id`. Implemented as: `login_24h_attendee_ids = {u.attendee_id for active users}`; `magic_24h = attendees active in 24h whose id not in login_24h_attendee_ids`; `active_today = len(active_user_ids) + len(magic_24h)`.
- `cumulative_active` = distinct ever-active = same union logic without the 24h filter (any non-null `last_login_at` user + any non-null `last_seen_at` attendee not linked to such a user).

Returns a stats dict (so the cron heartbeat records it).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_snapshot.py
"""usage_snapshot.compute_and_upsert_usage_daily — correctness + idempotency."""

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.services.usage_snapshot as us


class _Scalar:
    """Wrap a scalar value for `(await db.execute(...)).scalar()`."""
    def __init__(self, v): self._v = v
    def scalar(self): return self._v


class _Rows:
    """Wrap rows for `(await db.execute(...)).all()` returning (a, b) tuples."""
    def __init__(self, rows): self._rows = rows
    def all(self): return self._rows


def _make_db(*, total, real, users_active, attendees_active, upsert_sink):
    """users_active: list[(attendee_id_or_None, last_login_at)].
    attendees_active: list[(attendee_id, last_seen_at)].
    The service issues, in order:
      1. count(users)               -> .scalar()
      2. count(real users)          -> .scalar()
      3. select user (attendee_id, last_login_at) where last_login_at not null -> .all()
      4. select attendee (id, last_seen_at) where last_seen_at not null        -> .all()
      5. upsert INSERT ... ON CONFLICT (text())                                -> append to sink
    """
    db = AsyncMock()
    seq = [
        _Scalar(total),
        _Scalar(real),
        _Rows(users_active),
        _Rows(attendees_active),
        None,  # the upsert execute() return is unused
    ]
    async def _execute(stmt, params=None):
        out = seq.pop(0)
        if out is None:  # the upsert
            upsert_sink.append(params)
        return out
    db.execute.side_effect = _execute
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_snapshot_counts_distinct_people_no_double_count():
    aid = uuid.uuid4()
    now = datetime.utcnow()
    sink = []
    # One person logged in AND opened magic link (linked via attendee_id=aid):
    # should count ONCE, not twice.
    db = _make_db(
        total=10, real=8,
        users_active=[(aid, now - timedelta(hours=1))],
        attendees_active=[(aid, now - timedelta(hours=2))],
        upsert_sink=sink,
    )
    stats = await us.compute_and_upsert_usage_daily(db)
    assert stats["total_accounts"] == 10
    assert stats["real_accounts"] == 8
    assert stats["active_today"] == 1        # de-duped
    assert stats["cumulative_active"] == 1
    db.commit.assert_awaited()
    # the upsert was issued with the computed values
    assert sink and sink[0]["total_accounts"] == 10
    assert sink[0]["active_today"] == 1


@pytest.mark.asyncio
async def test_snapshot_magic_only_attendee_counts():
    aid = uuid.uuid4()
    now = datetime.utcnow()
    sink = []
    # A magic-link-only attendee (no user row) active in 24h.
    db = _make_db(
        total=5, real=5,
        users_active=[],
        attendees_active=[(aid, now - timedelta(hours=3))],
        upsert_sink=sink,
    )
    stats = await us.compute_and_upsert_usage_daily(db)
    assert stats["active_today"] == 1
    assert stats["cumulative_active"] == 1


@pytest.mark.asyncio
async def test_snapshot_excludes_stale_from_active_today():
    now = datetime.utcnow()
    sink = []
    db = _make_db(
        total=5, real=5,
        users_active=[(None, now - timedelta(days=3))],   # ever-active but stale
        attendees_active=[],
        upsert_sink=sink,
    )
    stats = await us.compute_and_upsert_usage_daily(db)
    assert stats["active_today"] == 0        # outside 24h
    assert stats["cumulative_active"] == 1   # still ever-active


@pytest.mark.asyncio
async def test_snapshot_upsert_is_idempotent_text():
    """The upsert must be ON CONFLICT (day) DO UPDATE so a same-day re-run
    overwrites rather than erroring."""
    now = datetime.utcnow()
    sink = []
    db = _make_db(
        total=1, real=1, users_active=[(None, now)], attendees_active=[],
        upsert_sink=sink,
    )
    captured = {}
    orig = db.execute.side_effect
    async def _spy(stmt, params=None):
        captured["last_sql"] = str(stmt)
        return await orig(stmt, params)
    db.execute.side_effect = _spy
    await us.compute_and_upsert_usage_daily(db)
    assert "ON CONFLICT" in captured["last_sql"].upper()
    assert "DO UPDATE" in captured["last_sql"].upper()
```

- [ ] **Step 2: Run it** — `pytest tests/test_usage_snapshot.py -v`. Expected: **FAIL** — `ModuleNotFoundError: No module named 'app.services.usage_snapshot'`.

- [ ] **Step 3: Implement (complete code)**

```python
# backend/app/services/usage_snapshot.py
"""Daily usage snapshot — writes one usage_daily row per UTC day.

"last_active" for a person = max(users.last_login_at, attendees.last_seen_at)
for their linked rows. A person who both logged in and opened a magic link is
counted once (we de-dupe on the attendee link). Magic-link-only users (no
account) are counted via attendees.last_seen_at.

See docs/superpowers/specs/2026-05-24-adoption-usage-tracking-design.md.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.attendee import Attendee

logger = logging.getLogger(__name__)

_DEMO_SUFFIX = "@demo.proofoftalk.io"


async def compute_and_upsert_usage_daily(db: AsyncSession) -> dict:
    """Compute today's usage_daily row and upsert it (idempotent on `day`).
    Returns a stats dict for the cron heartbeat."""
    now = datetime.utcnow()
    today = now.date()
    cutoff = now - timedelta(hours=24)

    total_accounts = (await db.execute(select(func.count(User.id)))).scalar() or 0
    real_accounts = (
        await db.execute(
            select(func.count(User.id)).where(
                User.is_admin.is_(False),
                ~func.lower(User.email).like(f"%{_DEMO_SUFFIX}"),
            )
        )
    ).scalar() or 0

    # Ever-active users: (attendee_id, last_login_at). attendee_id may be None.
    user_rows = (
        await db.execute(
            select(User.attendee_id, User.last_login_at).where(
                User.last_login_at.isnot(None)
            )
        )
    ).all()
    # Ever-active attendees: (id, last_seen_at).
    att_rows = (
        await db.execute(
            select(Attendee.id, Attendee.last_seen_at).where(
                Attendee.last_seen_at.isnot(None)
            )
        )
    ).all()

    # De-dupe a person who appears as both a logged-in user and a seen
    # attendee, via the user's attendee_id link.
    login_attendee_ids = {r[0] for r in user_rows if r[0] is not None}

    cumulative_active = len(user_rows) + sum(
        1 for (aid, _seen) in att_rows if aid not in login_attendee_ids
    )

    active_user_count = sum(1 for (_aid, ts) in user_rows if ts and ts >= cutoff)
    login_attendee_ids_24h = {
        r[0] for r in user_rows if r[0] is not None and r[1] and r[1] >= cutoff
    }
    active_magic_count = sum(
        1 for (aid, seen) in att_rows
        if seen and seen >= cutoff and aid not in login_attendee_ids_24h
    )
    active_today = active_user_count + active_magic_count

    await db.execute(
        text("""
            INSERT INTO usage_daily
                (day, total_accounts, real_accounts, active_today, cumulative_active)
            VALUES
                (:day, :total_accounts, :real_accounts, :active_today, :cumulative_active)
            ON CONFLICT (day) DO UPDATE SET
                total_accounts    = EXCLUDED.total_accounts,
                real_accounts     = EXCLUDED.real_accounts,
                active_today      = EXCLUDED.active_today,
                cumulative_active = EXCLUDED.cumulative_active
        """),
        {
            "day": today,
            "total_accounts": total_accounts,
            "real_accounts": real_accounts,
            "active_today": active_today,
            "cumulative_active": cumulative_active,
        },
    )
    await db.commit()

    stats = {
        "day": today.isoformat(),
        "total_accounts": total_accounts,
        "real_accounts": real_accounts,
        "active_today": active_today,
        "cumulative_active": cumulative_active,
    }
    logger.info("usage_snapshot: %s", stats)
    return stats
```

- [ ] **Step 4: Run the test** — `pytest tests/test_usage_snapshot.py -v`. Expected: **PASS** (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/usage_snapshot.py backend/tests/test_usage_snapshot.py
git commit -m "feat: usage_snapshot service — idempotent daily usage_daily upsert"
```

---

### Task 6: Register the daily snapshot cron in `app/main.py`

**Files:**
- Modify: `backend/app/main.py` (job functions ~line 124–130, `scheduler.add_job` block ~line 145–155, lifespan log ~line 160)
- Test: `backend/tests/test_usage_cron_registration.py`

Mirror the existing pattern exactly: a `_daily_usage_snapshot()` wrapper that opens its own `async_session()` and runs through `_run_with_heartbeat("daily_usage_snapshot", ...)`; scheduled at **03:45 UTC** (after match refresh at 03:30) with `**_JOB_DEFAULTS`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_usage_cron_registration.py
"""The daily usage-snapshot cron must be wired into main.py's scheduler and
run through the heartbeat wrapper (so a silent failure is visible)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.main as main


def test_usage_snapshot_job_is_scheduled():
    funcs = {j.func for j in main.scheduler.get_jobs()}
    assert main._daily_usage_snapshot in funcs, "usage snapshot cron not registered"
    job = next(j for j in main.scheduler.get_jobs() if j.func is main._daily_usage_snapshot)
    # CronTrigger fields expose hour/minute; assert 03:45 UTC.
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "3"
    assert fields["minute"] == "45"


@pytest.mark.asyncio
async def test_daily_usage_snapshot_runs_through_heartbeat():
    with patch.object(main, "_run_with_heartbeat", AsyncMock()) as hb, \
         patch("app.services.usage_snapshot.compute_and_upsert_usage_daily", AsyncMock()):
        await main._daily_usage_snapshot()
    hb.assert_awaited_once()
    assert hb.await_args.args[0] == "daily_usage_snapshot"
```

- [ ] **Step 2: Run it** — `pytest tests/test_usage_cron_registration.py -v`. Expected: **FAIL** — `AttributeError: module 'app.main' has no attribute '_daily_usage_snapshot'`.

- [ ] **Step 3: Implement (complete code)**

In `backend/app/main.py`, after the `_daily_match_refresh` function (ends line 130), add:

```python
async def _daily_usage_snapshot():
    from app.core.database import async_session
    from app.services.usage_snapshot import compute_and_upsert_usage_daily
    async def _go():
        async with async_session() as db:
            return await compute_and_upsert_usage_daily(db)
    await _run_with_heartbeat("daily_usage_snapshot", _go)
```

After the `_daily_match_refresh` `add_job` line (line 155), add:

```python
# Usage snapshot at 03:45 UTC — runs AFTER match refresh so it captures a
# full day of login/magic-link activity into usage_daily (one row/day).
scheduler.add_job(_daily_usage_snapshot,    CronTrigger(hour=3, minute=45, timezone="UTC"), **_JOB_DEFAULTS)
```

Update the lifespan log line (line 160) to mention the new job:

```python
    logger.info("scheduler: started — extasy 02:00, speakers 02:15, grid audit 02:30, enrichment 03:00, match refresh 03:30, usage snapshot 03:45 (UTC)")
```

- [ ] **Step 4: Run the test** — `pytest tests/test_usage_cron_registration.py -v`. Expected: **PASS** (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_usage_cron_registration.py
git commit -m "feat: schedule daily usage_daily snapshot cron (03:45 UTC) with heartbeat"
```

---

### Task 7: `GET /dashboard/adoption` endpoint

**Files:**
- Modify: `backend/app/api/routes/dashboard.py` (add a new route; place near `/stats`, e.g. after `get_stats`)
- Test: `backend/tests/test_adoption_endpoint.py`

Admin-gated (`require_admin`). Returns the exact JSON from the spec. Live counts are computed directly (so the endpoint is correct even before the cron has run); `signups_by_day` from `users.created_at`; `usage_by_day` and `tracking_started_at` from `usage_daily` (falling back to `today` if empty). `directory_size` = `COUNT(attendees)`. `pct_of_directory` = `real / directory_size * 100` (0.0 when directory empty).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_adoption_endpoint.py
"""GET /dashboard/adoption — admin-gating, shape, real/demo exclusion, pct math."""

from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.api.routes.dashboard as dash


class _Scalar:
    def __init__(self, v): self._v = v
    def scalar(self): return self._v


class _Rows:
    def __init__(self, rows): self._rows = rows
    def all(self): return self._rows


def _make_db():
    """Sequence the queries the handler issues, in order:
      1. count(users)                      -> .scalar()  (accounts.total)
      2. count(real users)                 -> .scalar()  (accounts.real)
      3. count(users where attendee_id not null) -> .scalar() (linked_to_attendee)
      4. count(attendees)                  -> .scalar()  (directory_size)
      5. signups_by_day group-by           -> .all()  [(date, n)]
      6. count(distinct login_active)      -> .scalar()
      7. count(distinct magic_active)      -> .scalar()
      8. usage_by_day select from usage_daily -> .all() [(day, active_today, cumulative_active)]
    """
    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(162),                                   # total
        _Scalar(154),                                   # real
        _Scalar(161),                                   # linked_to_attendee
        _Scalar(912),                                   # directory_size
        _Rows([(date(2026, 5, 21), 46), (date(2026, 5, 22), 50)]),  # signups
        _Scalar(3),                                     # login_active
        _Scalar(7),                                     # magic_link_active
        _Rows([                                         # usage_by_day
            (date(2026, 5, 24), 4, 9),
        ]),
    ]
    return db


@pytest.mark.asyncio
async def test_adoption_shape_and_pct_math():
    db = _make_db()
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))

    assert out["accounts"]["total"] == 162
    assert out["accounts"]["real"] == 154
    assert out["accounts"]["linked_to_attendee"] == 161
    assert out["accounts"]["directory_size"] == 912
    assert out["accounts"]["pct_of_directory"] == round(154 / 912 * 100, 1)

    assert out["signups_by_day"] == [
        {"day": "2026-05-21", "n": 46},
        {"day": "2026-05-22", "n": 50},
    ]

    assert out["usage"]["login_active"] == 3
    assert out["usage"]["magic_link_active"] == 7
    # cumulative_active / active_last_7d derived from usage_by_day (latest row)
    assert out["usage"]["cumulative_active"] == 9

    assert out["usage_by_day"] == [
        {"day": "2026-05-24", "active_today": 4, "cumulative_active": 9},
    ]
    assert out["tracking_started_at"] == "2026-05-24"  # min(day) in usage_daily


@pytest.mark.asyncio
async def test_adoption_empty_usage_falls_back_to_today():
    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(0), _Scalar(0), _Scalar(0), _Scalar(0),  # accounts + directory
        _Rows([]),                                         # signups
        _Scalar(0), _Scalar(0),                            # usage live
        _Rows([]),                                         # usage_by_day EMPTY
    ]
    out = await dash.get_adoption(db=db, _admin=SimpleNamespace(is_admin=True))
    assert out["usage_by_day"] == []
    assert out["accounts"]["pct_of_directory"] == 0.0   # no div-by-zero
    assert out["tracking_started_at"] == datetime.utcnow().date().isoformat()
    assert out["usage"]["cumulative_active"] == 0


def test_adoption_requires_admin_dependency():
    """The route is wired with require_admin (not require_auth)."""
    import inspect
    sig = inspect.signature(dash.get_adoption)
    dep = sig.parameters["_admin"].default
    # FastAPI Depends wraps the callable; assert it points at require_admin.
    assert getattr(dep, "dependency", None) is dash.require_admin
```

- [ ] **Step 2: Run it** — `pytest tests/test_adoption_endpoint.py -v`. Expected: **FAIL** — `AttributeError: module 'app.api.routes.dashboard' has no attribute 'get_adoption'`.

- [ ] **Step 3: Implement (complete code)**

In `backend/app/api/routes/dashboard.py`, add (e.g. right after `get_stats`, before `_compute_kpi_rates` is already above it — place it after the `get_stats` function body). The handler signature must be `async def get_adoption(db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin))`:

```python
@router.get("/adoption")
async def get_adoption(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Admin-only adoption + usage metrics. Account/signup numbers are
    historical (correct immediately); usage numbers start at zero and grow
    from tracking-start forward. See the adoption-usage-tracking design."""
    from datetime import datetime as _dt
    from sqlalchemy import text as _text
    from app.models.user import User as _User
    from app.models.usage_daily import UsageDaily

    _DEMO = "@demo.proofoftalk.io"

    total = (await db.execute(select(func.count(_User.id)))).scalar() or 0
    real = (
        await db.execute(
            select(func.count(_User.id)).where(
                _User.is_admin.is_(False),
                ~func.lower(_User.email).like(f"%{_DEMO}"),
            )
        )
    ).scalar() or 0
    linked = (
        await db.execute(
            select(func.count(_User.id)).where(_User.attendee_id.isnot(None))
        )
    ).scalar() or 0
    directory_size = (await db.execute(select(func.count(Attendee.id)))).scalar() or 0
    pct_of_directory = round(real / directory_size * 100, 1) if directory_size else 0.0

    # Signups by day — historical, from users.created_at.
    signup_rows = (
        await db.execute(
            select(
                func.date(_User.created_at).label("day"),
                func.count(_User.id).label("n"),
            )
            .group_by(func.date(_User.created_at))
            .order_by(func.date(_User.created_at))
        )
    ).all()
    signups_by_day = [
        {"day": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]), "n": r[1]}
        for r in signup_rows
    ]

    # Live usage counts (correct even before the cron has run).
    login_active = (
        await db.execute(
            select(func.count(_User.id)).where(_User.last_login_at.isnot(None))
        )
    ).scalar() or 0
    magic_link_active = (
        await db.execute(
            select(func.count(Attendee.id)).where(Attendee.last_seen_at.isnot(None))
        )
    ).scalar() or 0

    # Usage-by-day history from the snapshot table.
    usage_rows = (
        await db.execute(
            select(
                UsageDaily.day, UsageDaily.active_today, UsageDaily.cumulative_active
            ).order_by(UsageDaily.day)
        )
    ).all()
    usage_by_day = [
        {
            "day": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
            "active_today": r[1],
            "cumulative_active": r[2],
        }
        for r in usage_rows
    ]

    if usage_by_day:
        tracking_started_at = usage_by_day[0]["day"]
        latest = usage_by_day[-1]
        cumulative_active = latest["cumulative_active"]
        active_last_7d = sum(d["active_today"] for d in usage_by_day[-7:])
    else:
        tracking_started_at = _dt.utcnow().date().isoformat()
        cumulative_active = 0
        active_last_7d = 0

    return {
        "tracking_started_at": tracking_started_at,
        "accounts": {
            "total": total,
            "real": real,
            "linked_to_attendee": linked,
            "pct_of_directory": pct_of_directory,
            "directory_size": directory_size,
        },
        "signups_by_day": signups_by_day,
        "usage": {
            "cumulative_active": cumulative_active,
            "active_last_7d": active_last_7d,
            "magic_link_active": magic_link_active,
            "login_active": login_active,
        },
        "usage_by_day": usage_by_day,
    }
```

> Note: the test's `_make_db` sequences exactly 8 `execute()` calls in this order: count(users), count(real), count(linked), count(attendees), signups group-by, login_active, magic_link_active, usage_by_day. Keep the query order in the implementation matching that sequence.

- [ ] **Step 4: Run the test** — `pytest tests/test_adoption_endpoint.py -v`. Expected: **PASS** (3 passed).

- [ ] **Step 5: Smoke-test the whole backend suite** — `pytest -q`. Expected: all green (new + existing).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/dashboard.py backend/tests/test_adoption_endpoint.py
git commit -m "feat: GET /dashboard/adoption — admin-only accounts + usage metrics"
```

---

### Task 8: Frontend — type + hook + "Adoption & Usage" card

**Files:**
- Modify: `frontend/src/types/index.ts` (add `Adoption` interface after `MatchQuality`, ~line 75)
- Modify: `frontend/src/api/client.ts` (add `getAdoption` near `getRevenueStats`, ~line 238)
- Modify: `frontend/src/hooks/useDashboard.ts` (add `useAdoption`)
- Modify: `frontend/src/pages/Dashboard.tsx` (import `getAdoption`/`useAdoption`, render card inside the `revenueData &&` `<>` block — placed right after the Sync Health card, ~line 502)

No frontend unit-test harness exists; the verification is a clean type-check + build (`tsc -b && vite build`).

- [ ] **Step 1: Add the type** — in `frontend/src/types/index.ts`, after the `MatchQuality` interface:

```typescript
export interface Adoption {
  tracking_started_at: string;
  accounts: {
    total: number;
    real: number;
    linked_to_attendee: number;
    pct_of_directory: number;
    directory_size: number;
  };
  signups_by_day: { day: string; n: number }[];
  usage: {
    cumulative_active: number;
    active_last_7d: number;
    magic_link_active: number;
    login_active: number;
  };
  usage_by_day: { day: string; active_today: number; cumulative_active: number }[];
}
```

- [ ] **Step 2: Add the API client function** — in `frontend/src/api/client.ts`, after `getRevenueStats` (~line 238). Add the import of the type at the existing types import (top of file) if needed, or use the inline-typed return. Use the shared `Adoption` type:

```typescript
export async function getAdoption(): Promise<Adoption> {
  const { data } = await api.get("/dashboard/adoption");
  return data;
}
```

Ensure `Adoption` is imported at the top of `client.ts` (it imports types from `../types` already — add `Adoption` to that import list).

- [ ] **Step 3: Add the React Query hook** — in `frontend/src/hooks/useDashboard.ts`, import `getAdoption` from `../api/client` and add:

```typescript
export function useAdoption() {
  return useQuery({
    queryKey: ["adoption"],
    queryFn: getAdoption,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });
}
```

(Add `getAdoption` to the existing `import { ... } from "../api/client"` block.)

- [ ] **Step 4: Render the card** — in `frontend/src/pages/Dashboard.tsx`:

  1. Add `useAdoption` to the `../hooks/useDashboard` import (line 8–11) and add `getAdoption` is not needed there (hook handles it). Add a `UserPlus` / `LogIn` icon to the lucide import (line 4–6) — use `UserPlus` and `Activity` (Activity is already imported).
  2. In the component body (after `const { data: quality } = useMatchQuality();`, line 72), add:

```tsx
  const { data: adoption } = useAdoption();
```

  3. Inside the `{revenueData && ( <> ... )}` block, immediately after the Sync Health card closes (after line 502), insert the card. (Render gated on `adoption`, not `revenueData` — but it lives inside the same fragment for layout; if you prefer it independent, render it just before the `{revenueData && (` block. Either works; below assumes inside, right after Sync Health.)

```tsx
          {/* Adoption & Usage — accounts created + signup trend (historical),
              plus real usage (logins + magic-link opens) anchored to the
              tracking-start date. Usage numbers start at 0 and grow forward;
              they are NOT a 30-day window (we have no pre-launch history). */}
          {adoption && (
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <UserPlus className="w-5 h-5 text-[#E76315]" />
                <h2 className="text-lg font-semibold">Adoption &amp; Usage</h2>
                <span className="text-[10px] text-white/30">admin only</span>
              </div>

              {/* Accounts top line */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.accounts.total}</div>
                  <div className="text-[10px] text-white/40 uppercase">Accounts</div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.accounts.real}</div>
                  <div className="text-[10px] text-white/40 uppercase">Real (excl. admin/demo)</div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.accounts.pct_of_directory}%</div>
                  <div className="text-[10px] text-white/40 uppercase">of {adoption.accounts.directory_size} directory</div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.accounts.linked_to_attendee}</div>
                  <div className="text-[10px] text-white/40 uppercase">Linked to profile</div>
                </div>
              </div>

              {/* Signup trend — historical, shows the welcome-email spike. */}
              {adoption.signups_by_day.length > 0 && (
                <div className="mb-5">
                  <div className="text-xs font-semibold text-white/60 mb-2">Signups by day</div>
                  <div className="space-y-1.5">
                    {adoption.signups_by_day.map(({ day, n }) => {
                      const maxN = Math.max(...adoption.signups_by_day.map((d) => d.n), 1);
                      const label = (() => {
                        try {
                          return new Date(day).toLocaleDateString("en-GB", { month: "short", day: "numeric" });
                        } catch { return day; }
                      })();
                      return (
                        <div key={day} className="flex items-center gap-2">
                          <span className="w-14 text-[10px] text-white/40 text-right shrink-0">{label}</span>
                          <div className="flex-1 h-5 bg-white/5 rounded overflow-hidden relative">
                            <div className="h-full bg-[#E76315] rounded transition-all" style={{ width: `${(n / maxN) * 100}%` }} />
                            <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white/70">{n}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Usage block — anchored to tracking start. */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.usage.cumulative_active}</div>
                  <div className="text-[10px] text-white/40 uppercase">Active (since tracking began {adoption.tracking_started_at})</div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.usage.active_last_7d}</div>
                  <div className="text-[10px] text-white/40 uppercase">Active last 7d (since tracking began {adoption.tracking_started_at})</div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.usage.login_active}</div>
                  <div className="text-[10px] text-white/40 uppercase">Logged in</div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                  <div className="text-2xl font-bold">{adoption.usage.magic_link_active}</div>
                  <div className="text-[10px] text-white/40 uppercase">Magic-link opens</div>
                </div>
              </div>

              {/* Day-by-day usage trend, once usage_daily has rows; else explainer. */}
              {adoption.usage_by_day.length > 0 ? (
                <div className="mt-5">
                  <div className="text-xs font-semibold text-white/60 mb-2">Daily active</div>
                  <div className="space-y-1.5">
                    {adoption.usage_by_day.map(({ day, active_today }) => {
                      const maxA = Math.max(...adoption.usage_by_day.map((d) => d.active_today), 1);
                      const label = (() => {
                        try {
                          return new Date(day).toLocaleDateString("en-GB", { month: "short", day: "numeric" });
                        } catch { return day; }
                      })();
                      return (
                        <div key={day} className="flex items-center gap-2">
                          <span className="w-14 text-[10px] text-white/40 text-right shrink-0">{label}</span>
                          <div className="flex-1 h-5 bg-white/5 rounded overflow-hidden relative">
                            <div className="h-full bg-emerald-500 rounded transition-all" style={{ width: `${(active_today / maxA) * 100}%` }} />
                            <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white/70">{active_today}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="mt-5 p-3 rounded-lg bg-white/[0.02] border border-white/5 text-xs text-white/40">
                  Usage tracking started {adoption.tracking_started_at} — numbers build from here. The daily snapshot fills this in from day one.
                </div>
              )}
            </div>
          )}
```

  4. Add `UserPlus` to the lucide-react import at the top of the file (line 4–6):

```tsx
import {
  Users, Handshake, Check, TrendingUp, BarChart3, Brain,
  Lightbulb, DollarSign, Activity, Zap, RefreshCw, X, Sparkles, Download, UserPlus,
} from "lucide-react";
```

- [ ] **Step 5: Type-check + build** — Expected: **clean** (no TS errors, build succeeds).

```bash
cd frontend && npm run build
```
(`npm run build` runs `tsc -b && vite build`.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/hooks/useDashboard.ts frontend/src/pages/Dashboard.tsx
git commit -m "feat: Adoption & Usage dashboard card (accounts, signup trend, usage)"
```

---

## Living-docs update (after the feature is verified end-to-end)

Per the project's non-negotiable post-change checklist, before declaring done:

- [ ] Append a dated entry to `session_log.md` summarising the adoption-tracking feature.
- [ ] Update `whats_next.md` — move adoption-tracking items to Done, re-prioritise Now.
- [ ] Update `project_state.md` — note the new endpoint, columns, table, cron, and that usage numbers grow from tracking-start.
- [ ] Commit docs together: `git add session_log.md whats_next.md project_state.md && git commit -m "docs: adoption & usage tracking shipped"`.

---

## Self-review — spec coverage

| Spec requirement | Covered by |
|---|---|
| Accounts created + count surfaced | Task 7 (`accounts.total/real/linked_to_attendee`), Task 8 card |
| Signup trend (from `users.created_at`) | Task 7 (`signups_by_day`), Task 8 sparkline |
| Record password logins (`last_login_at`) | Tasks 1–3 |
| Record magic-link opens (`last_seen_at`) — the majority path | Tasks 1–2, 4 |
| Throttled writes (NULL or >1h) | Task 3 + Task 4 (tests pin throttle) |
| Best-effort writes never break the response | Task 3 (`test_login_hook_failure...`), Task 4 (`test_magic_open_hook_failure...`) |
| `usage_daily` table (day/total/real/active_today/cumulative_active) | Task 1 (migration), Task 2 (model) |
| Daily snapshot, idempotent on `day` | Task 5 (`ON CONFLICT (day) DO UPDATE`, idempotency test) |
| Snapshot de-dupes a person active via both paths | Task 5 (`test_snapshot_counts_distinct_people_no_double_count`) |
| Cron + `sync_status` heartbeat (matches existing crons) | Task 6 (`_run_with_heartbeat("daily_usage_snapshot", ...)`) |
| Endpoint JSON shape per spec | Task 7 (shape test) |
| Anchored to tracking-start, NOT a 30-day window | Task 7 (`tracking_started_at` from `min(day)`/today; `active_last_7d` summed from snapshot history), Task 8 labels |
| Honest empty/explainer state pre-accumulation | Task 8 ("Usage tracking started … — numbers build from here") |
| "since tracking began <date>" labels | Task 8 usage block labels |
| Admin-only (privacy: usage timestamps never attendee-facing) | Task 7 (`require_admin` + gating test); no attendee-facing surface added |
| Real-vs-demo exclusion | Task 7 (`is_admin` + `@demo.proofoftalk.io` filter, exclusion test), Task 5 (`real_accounts` same rule) |
| `pct_of_directory` math (+ no div-by-zero) | Task 7 (pct test + empty-directory test) |
| Endpoint degrades gracefully when `usage_daily` empty | Task 7 (`test_adoption_empty_usage_falls_back_to_today`) |

**Gaps found and fixed during self-review:**

1. **`active_last_7d` source was ambiguous in the spec** (rolling vs since-launch). Pinned it to `sum(active_today over the last ≤7 snapshot rows)` so in week one it naturally equals "since launch" without implying pre-launch history — matches the spec's "in week 1 ≈ since-launch" note. (Task 7.)
2. **Double-counting a person active via both login and magic link.** The spec defines `last_active = max(last_login_at, last_seen_at)` per person; a naive sum would double-count. Added explicit de-dup on the user→attendee link in Task 5 with a dedicated test.
3. **`alembic/env.py` model registration** — the new `UsageDaily` model won't be picked up by `Base.metadata` (and future autogenerate) unless imported in `env.py`, mirroring the existing `GridAuditRun` import. Added as Task 2 Step 6 (with an ordering note in Task 1 Step 3 to avoid an import error).
4. **`real_accounts` rule consistency** — the snapshot table and the live endpoint both must use the *same* "not admin AND not `@demo.proofoftalk.io`" rule; pinned identically in Task 5 and Task 7 (and called out in the column/key contract).
5. **No-test-DB constraint for the migration** — replaced an `alembic upgrade` smoke test (would touch the DB, disallowed) with an import + structural assertion (Task 1).
