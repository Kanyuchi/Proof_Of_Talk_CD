# Sponsor Self-Service Invite Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Work in an isolated worktree/branch — do NOT implement on `main`.** `main` currently carries 60+ uncommitted files from other parallel sessions. Create a worktree first (superpowers:using-git-worktrees).

**Goal:** Ship a single shared `/join/<code>` link that lets anyone (sponsors) self-register a full login account with no pre-existing row, and on save runs the full enrichment + matching pipeline — plus make every profile save, for everyone, refresh matches immediately.

**Architecture:** A new `SPONSOR_INVITE_CODE` env var gates a new `POST /auth/join` endpoint (constant-time compare, bypasses the ticket gate, forces `ticket_type=SPONSOR`). Two detached background functions in a new `app/services/profile_pipeline.py` — `refresh_profile_matches` (light: re-embed + rematch) wired into every save surface, and `run_full_enrichment` (cold-start: Grid + website, then refresh) used by join. A new `SponsorJoin.tsx` page posts to `/auth/join`.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest + pytest-asyncio (mock-based route tests), React 18 + TypeScript + Vite + Tailwind, axios.

**Spec:** `docs/superpowers/specs/2026-05-22-sponsor-invite-link-design.md`

**Test convention (house style — follow exactly):** route handlers are tested by calling the *undecorated coroutine* (`module.handler.__wrapped__(...)` when `@limiter.limit` is present; call directly when not), passing an `AsyncMock()` db and a `_ScalarResult` helper for `.scalars().first()`. Sequence multiple queries with `db.execute.side_effect = [...]`. Patch external services and `asyncio.create_task`. See `tests/test_auth_forgot_password.py` for the canonical example.

**Run tests:** `cd backend && source .venv/bin/activate && pytest <path> -v`

---

### Task 1: `refresh_profile_matches` — the light re-embed + rematch path

**Files:**
- Create: `backend/app/services/profile_pipeline.py`
- Test: `backend/tests/test_profile_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_profile_pipeline.py
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.profile_pipeline as pp


def _fake_session(db):
    """Return a callable that mimics `async_session()` as an async context
    manager yielding `db`."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=db)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


@pytest.mark.asyncio
async def test_refresh_profile_matches_reembeds_then_matches():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid)
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    engine = MagicMock()
    engine.process_attendee = AsyncMock()
    engine.generate_matches_for_attendee = AsyncMock()
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "MatchingEngine", MagicMock(return_value=engine)):
        await pp.refresh_profile_matches(aid)
    engine.process_attendee.assert_awaited_once_with(attendee)
    engine.generate_matches_for_attendee.assert_awaited_once_with(
        aid, top_k=10, notify=False
    )


@pytest.mark.asyncio
async def test_refresh_profile_matches_noop_when_attendee_missing():
    aid = uuid.uuid4()
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    engine = MagicMock()
    engine.process_attendee = AsyncMock()
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "MatchingEngine", MagicMock(return_value=engine)):
        await pp.refresh_profile_matches(aid)
    engine.process_attendee.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_profile_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.profile_pipeline'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/profile_pipeline.py
"""Detached profile-enrichment + match-refresh triggers.

Two functions, run via asyncio.create_task (NOT FastAPI BackgroundTasks —
that holds the request worker through a 10-20s OpenAI/Grid pipeline and 504s
the edge):

- refresh_profile_matches: LIGHT path. Re-embed from the current profile and
  regenerate matches. No re-scraping. Used by every profile save and as
  stages 2-3 of the cold-start join.
- run_full_enrichment: COLD-START path. Grid + website enrichment, then
  refresh_profile_matches. Used by the sponsor join (no enrichment data yet).
"""
import logging
import uuid

from app.core.database import async_session
from app.models.attendee import Attendee
from app.services.matching import MatchingEngine
from app.services.enrichment import EnrichmentService

logger = logging.getLogger(__name__)


async def refresh_profile_matches(attendee_id: uuid.UUID) -> None:
    try:
        async with async_session() as db:
            engine = MatchingEngine(db)
            attendee = await db.get(Attendee, attendee_id)
            if not attendee:
                return
            await engine.process_attendee(attendee)
            await engine.generate_matches_for_attendee(
                attendee_id, top_k=10, notify=False
            )
    except Exception as exc:
        logger.exception("refresh_profile_matches failed for %s: %s", attendee_id, exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_profile_pipeline.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/profile_pipeline.py backend/tests/test_profile_pipeline.py
git commit -m "feat: refresh_profile_matches light re-embed + rematch trigger"
```

---

### Task 2: `run_full_enrichment` — the cold-start path

**Files:**
- Modify: `backend/app/services/profile_pipeline.py`
- Test: `backend/tests/test_profile_pipeline.py`

- [ ] **Step 1: Write the failing test** (append to the test file)

```python
@pytest.mark.asyncio
async def test_run_full_enrichment_enriches_then_refreshes():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid, enriched_profile={})
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    svc = MagicMock()
    svc.enrich_attendee = AsyncMock(return_value={"grid": {"x": 1}})
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "EnrichmentService", MagicMock(return_value=svc)), \
         patch.object(pp, "refresh_profile_matches", AsyncMock()) as refresh:
        await pp.run_full_enrichment(aid)
    svc.enrich_attendee.assert_awaited_once_with(attendee)
    assert attendee.enriched_profile == {"grid": {"x": 1}}
    refresh.assert_awaited_once_with(aid)


@pytest.mark.asyncio
async def test_run_full_enrichment_still_refreshes_when_enrich_fails():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid, enriched_profile={})
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    svc = MagicMock()
    svc.enrich_attendee = AsyncMock(side_effect=RuntimeError("grid down"))
    with patch.object(pp, "async_session", _fake_session(db)), \
         patch.object(pp, "EnrichmentService", MagicMock(return_value=svc)), \
         patch.object(pp, "refresh_profile_matches", AsyncMock()) as refresh:
        await pp.run_full_enrichment(aid)
    refresh.assert_awaited_once_with(aid)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_profile_pipeline.py -k run_full_enrichment -v`
Expected: FAIL — `AttributeError: ... has no attribute 'run_full_enrichment'`

- [ ] **Step 3: Write minimal implementation** (append to `profile_pipeline.py`)

```python
async def run_full_enrichment(attendee_id: uuid.UUID) -> None:
    try:
        async with async_session() as db:
            attendee = await db.get(Attendee, attendee_id)
            if not attendee:
                return
            try:
                svc = EnrichmentService()
                # enrich_attendee returns a NEW dict; assigning it is required
                # for SQLAlchemy to detect the JSONB change (mutate-and-reassign
                # the same ref is a silent no-op).
                attendee.enriched_profile = await svc.enrich_attendee(attendee)
                await db.commit()
            except Exception:
                logger.exception(
                    "run_full_enrichment: enrich stage failed for %s", attendee_id
                )
    except Exception as exc:
        logger.exception("run_full_enrichment outer failure for %s: %s", attendee_id, exc)
    # Always attempt the embed + match refresh, even if the enrich stage failed.
    await refresh_profile_matches(attendee_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_profile_pipeline.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/profile_pipeline.py backend/tests/test_profile_pipeline.py
git commit -m "feat: run_full_enrichment cold-start enrichment trigger"
```

---

### Task 3: Config setting `SPONSOR_INVITE_CODE`

**Files:**
- Modify: `backend/app/core/config.py` (after `REQUIRE_TICKET_TO_REGISTER`, ~line 66)
- Modify: `backend/.env.example`

- [ ] **Step 1: Add the setting**

In `backend/app/core/config.py`, add after the `REQUIRE_TICKET_TO_REGISTER` field:

```python
    # Sponsor self-service invite. Blank = feature OFF (the /join endpoint and
    # the /join/<code> page both refuse). Set to an unguessable string
    # (e.g. `python -c "import secrets;print(secrets.token_urlsafe(24))"`) in
    # Railway env, then share https://meet.proofoftalk.io/join/<code>. Anyone
    # with the link self-registers a full SPONSOR account; rotating this value
    # revokes the old link.
    SPONSOR_INVITE_CODE: str = ""
```

- [ ] **Step 2: Document in `.env.example`**

Add to `backend/.env.example`:

```bash
# Sponsor self-service invite link. Blank = OFF. Set to an unguessable string,
# then share https://meet.proofoftalk.io/join/<this-value>
SPONSOR_INVITE_CODE=
```

- [ ] **Step 3: Verify it loads**

Run: `cd backend && source .venv/bin/activate && python -c "from app.core.config import get_settings; print(repr(get_settings().SPONSOR_INVITE_CODE))"`
Expected: `''`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/config.py backend/.env.example
git commit -m "feat: add SPONSOR_INVITE_CODE config (off by default)"
```

---

### Task 4: `JoinRequest` schema

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Test: `backend/tests/test_join_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_join_flow.py
import pytest
from pydantic import ValidationError

from app.schemas.auth import JoinRequest


def test_join_request_rejects_weak_password():
    with pytest.raises(ValidationError):
        JoinRequest(invite_code="x", email="a@b.com", password="weak", name="A")


def test_join_request_rejects_blank_name():
    with pytest.raises(ValidationError):
        JoinRequest(invite_code="x", email="a@b.com", password="Strong1pass", name="   ")


def test_join_request_valid_minimal():
    r = JoinRequest(invite_code="code", email="a@b.com", password="Strong1pass", name="Ann")
    assert r.invite_code == "code"
    assert r.email == "a@b.com"
    assert r.ticket_type == "SPONSOR"  # default for this schema
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_join_flow.py -v`
Expected: FAIL — `ImportError: cannot import name 'JoinRequest'`

- [ ] **Step 3: Write the schema**

In `backend/app/schemas/auth.py`, add after `RegisterRequest` (reuse the same validators by copying them — keep the file's existing per-class validator style):

```python
class JoinRequest(BaseModel):
    """Self-service sponsor onboarding via the shared invite link. Same profile
    fields as RegisterRequest plus `invite_code`; `ticket_type` defaults to
    SPONSOR and is forced server-side regardless."""
    invite_code: str
    # Account credentials
    email: EmailStr
    password: str
    # Attendee profile
    name: str
    company: str = ""
    title: str = ""
    ticket_type: str = "SPONSOR"
    interests: list[str] = []
    goals: str | None = None
    target_companies: str | None = None
    seeking: list[str] = []
    not_looking_for: list[str] = []
    preferred_geographies: list[str] = []
    deal_stage: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    company_website: str | None = None
    privacy_mode: str = "full"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("name")
    @classmethod
    def no_empty_strings(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank")
        return v.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_join_flow.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/tests/test_join_flow.py
git commit -m "feat: JoinRequest schema for sponsor self-service signup"
```

---

### Task 5: Extract `_upsert_attendee_from_payload` + point `register` at `refresh_profile_matches`

This refactors the working `register` path (auth.py:45-141). Add a regression test first.

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_join_flow.py`

- [ ] **Step 1: Write the failing test** (append to `test_join_flow.py`)

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import app.api.routes.auth as auth


class _ScalarResult:
    def __init__(self, row):
        self._row = row
    def scalars(self):
        return self
    def first(self):
        return self._row


def _reg_data(**over):
    base = dict(
        email="new@x.com", password="Strong1pass", name="Reg User", company="Co",
        title="CTO", ticket_type="delegate", interests=[], goals=None, seeking=[],
        not_looking_for=[], preferred_geographies=[], deal_stage=None,
        linkedin_url=None, twitter_handle=None, company_website=None,
        privacy_mode="full",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _fake_ct():
    """create_task stand-in that closes the coroutine (no warning) and records."""
    def _ct(coro):
        coro.close()
        return MagicMock()
    return MagicMock(side_effect=_ct)


@pytest.mark.asyncio
async def test_register_dispatches_refresh_profile_matches():
    data = _reg_data()
    db = AsyncMock()
    db.add = MagicMock()
    # 1st execute = User lookup (None), 2nd = Attendee lookup inside helper (None)
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(None)]
    ct = _fake_ct()
    with patch.object(auth, "get_settings",
                      lambda: SimpleNamespace(REQUIRE_TICKET_TO_REGISTER=False,
                                              SPONSOR_INVITE_CODE="")), \
         patch.object(auth, "get_password_hash", lambda p: "hashed"), \
         patch.object(auth, "create_access_token", lambda c: "jwt"), \
         patch.object(auth, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", ct):
        out = await auth.register.__wrapped__(SimpleNamespace(), data, None, db)
    assert out.access_token == "jwt"
    refresh.assert_called_once()          # coroutine constructed from refresh
    ct.assert_called_once()               # and handed to create_task
```

Note: `register`'s signature is `register(request, data, background_tasks, db)`. Pass `None` for `background_tasks` (unused on this path).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_join_flow.py::test_register_dispatches_refresh_profile_matches -v`
Expected: FAIL — `register` still calls `_process_attendee_bg` (an `AttributeError` on the patched `refresh_profile_matches`, or `refresh` not called).

- [ ] **Step 3: Add the helper, refactor `register`, update imports**

In `backend/app/api/routes/auth.py`:

(a) Add imports near the top (after the existing `from app.services.email import ...`):

```python
from app.schemas.auth import (
    RegisterRequest, LoginRequest, Token, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest, ClaimAccountRequest, JoinRequest,
)
from app.services.profile_pipeline import refresh_profile_matches, run_full_enrichment
```

(Replace the existing `from app.schemas.auth import ...` line with the one above to add `JoinRequest`.)

(b) Add the shared helper above `register`:

```python
async def _upsert_attendee_from_payload(
    db: AsyncSession,
    data,
    *,
    force_ticket_type: str | None,
    enforce_ticket_gate: bool,
) -> Attendee:
    """Create a new attendee from a register/join payload, or merge the payload
    onto an existing row at the same email. Uses getattr so it tolerates both
    RegisterRequest and JoinRequest. Caller is responsible for flush/commit.

    force_ticket_type: when set, overrides ticket_type on both new and existing
      rows (join forces "SPONSOR"). enforce_ticket_gate: when True, a new email
      with no attendee row is blocked by REQUIRE_TICKET_TO_REGISTER (register);
      join passes False because the invite code is the gate.
    """
    existing = (await db.execute(
        select(Attendee).where(Attendee.email == data.email)
    )).scalars().first()

    if existing:
        for field in ("name", "company", "title", "linkedin_url",
                      "twitter_handle", "company_website", "goals",
                      "deal_stage", "target_companies"):
            val = getattr(data, field, None)
            if val:
                setattr(existing, field, val)
        for list_field in ("interests", "seeking", "not_looking_for",
                           "preferred_geographies"):
            val = getattr(data, list_field, None)
            if val:
                setattr(existing, list_field, val)
        if getattr(data, "privacy_mode", None) in ("full", "b2b_only"):
            existing.privacy_mode = data.privacy_mode
        if force_ticket_type:
            existing.ticket_type = force_ticket_type
        if not existing.magic_access_token:
            existing.magic_access_token = secrets.token_urlsafe(32)
        return existing

    if enforce_ticket_gate and get_settings().REQUIRE_TICKET_TO_REGISTER:
        logger.info("register: blocked non-ticket email %s", data.email)
        raise HTTPException(
            status_code=403,
            detail=(
                "We couldn't find a Proof of Talk ticket for this email. "
                "Please register with the email address you used to buy your pass. "
                "If you believe this is an error, contact the Proof of Talk team."
            ),
        )

    pm = getattr(data, "privacy_mode", "full")
    attendee = Attendee(
        name=data.name,
        email=data.email,
        company=getattr(data, "company", "") or "",
        title=getattr(data, "title", "") or "",
        ticket_type=force_ticket_type or getattr(data, "ticket_type", "delegate"),
        interests=getattr(data, "interests", []) or [],
        goals=getattr(data, "goals", None),
        target_companies=getattr(data, "target_companies", None),
        seeking=getattr(data, "seeking", []) or [],
        not_looking_for=getattr(data, "not_looking_for", []) or [],
        preferred_geographies=getattr(data, "preferred_geographies", []) or [],
        deal_stage=getattr(data, "deal_stage", None),
        linkedin_url=getattr(data, "linkedin_url", None),
        twitter_handle=getattr(data, "twitter_handle", None),
        company_website=getattr(data, "company_website", None),
        magic_access_token=secrets.token_urlsafe(32),
        privacy_mode=pm if pm in ("full", "b2b_only") else "full",
    )
    db.add(attendee)
    return attendee
```

(c) Replace the body of `register` between the existing-User check and the `await db.flush()` line. That is, replace the whole `existing_attendee = (...)` block through the `db.add(attendee)`/else block (auth.py:63-120) with:

```python
    attendee = await _upsert_attendee_from_payload(
        db, data, force_ticket_type=None, enforce_ticket_gate=True,
    )
```

(d) Replace the fire-and-forget line (auth.py:138) from:

```python
    asyncio.create_task(_process_attendee_bg(attendee.id))
```

to:

```python
    # Re-embed + generate matches immediately so new registrants see matches
    # within seconds instead of waiting for the 02:45 UTC cron.
    asyncio.create_task(refresh_profile_matches(attendee.id))
```

(e) Delete the now-unused `_process_attendee_bg` function (auth.py:25-42) and its now-unused `from app.services.matching import MatchingEngine` import **only if no other code in auth.py uses MatchingEngine** (grep first: `grep -n MatchingEngine backend/app/api/routes/auth.py`). If other uses remain, keep the import.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_join_flow.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite (refactor touched a core path)**

Run: `pytest -q`
Expected: no new failures vs. baseline (run `pytest -q` once before this task to capture the baseline).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_join_flow.py
git commit -m "refactor: shared attendee upsert helper; register generates matches on signup"
```

---

### Task 6: `POST /auth/join` endpoint

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_join_flow.py`

- [ ] **Step 1: Write the failing tests** (append to `test_join_flow.py`)

```python
def _join_data(**over):
    base = dict(
        invite_code="secret-code", email="sam@sponsor.com", password="Strong1pass",
        name="Sam Sponsor", company="Acme", title="CEO", interests=[], goals=None,
        target_companies=None, seeking=[], not_looking_for=[],
        preferred_geographies=[], deal_stage=None, linkedin_url=None,
        twitter_handle=None, company_website=None, privacy_mode="full",
        ticket_type="SPONSOR",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _join_settings(code="secret-code"):
    return SimpleNamespace(SPONSOR_INVITE_CODE=code, REQUIRE_TICKET_TO_REGISTER=True)


async def _call_join(data, db, settings):
    with patch.object(auth, "get_settings", lambda: settings), \
         patch.object(auth, "get_password_hash", lambda p: "hashed"), \
         patch.object(auth, "create_access_token", lambda c: "jwt-token"), \
         patch.object(auth, "run_full_enrichment", AsyncMock()) as enrich, \
         patch("asyncio.create_task", _fake_ct()) as ct:
        out = await auth.join.__wrapped__(SimpleNamespace(), data, db)
    return out, enrich, ct


@pytest.mark.asyncio
async def test_join_creates_sponsor_account_and_dispatches_full_enrichment():
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(None)]  # no User, no Attendee
    out, enrich, ct = await _call_join(_join_data(), db, _join_settings())
    assert out.access_token == "jwt-token"
    added = [c.args[0] for c in db.add.call_args_list]
    attendee = next(a for a in added if isinstance(a, auth.Attendee))
    assert str(attendee.ticket_type) == "SPONSOR"
    assert attendee.magic_access_token
    enrich.assert_called_once()
    ct.assert_called_once()


@pytest.mark.asyncio
async def test_join_rejects_wrong_code():
    db = AsyncMock()
    with pytest.raises(auth.HTTPException) as exc:
        await _call_join(_join_data(invite_code="wrong"), db, _join_settings())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_join_disabled_when_code_unset():
    db = AsyncMock()
    with pytest.raises(auth.HTTPException) as exc:
        await _call_join(_join_data(), db, _join_settings(code=""))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_join_rejects_existing_user():
    db = AsyncMock()
    db.execute.side_effect = [_ScalarResult(SimpleNamespace(id="u1"))]  # User exists
    with pytest.raises(auth.HTTPException) as exc:
        await _call_join(_join_data(), db, _join_settings())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_join_merges_existing_attendee_and_tags_sponsor():
    existing = SimpleNamespace(
        email="sam@sponsor.com", name="Old", company="Old Co", title="",
        linkedin_url=None, twitter_handle=None, company_website=None, goals=None,
        deal_stage=None, target_companies=None, interests=[], seeking=[],
        not_looking_for=[], preferred_geographies=[], privacy_mode="full",
        magic_access_token=None, ticket_type="DELEGATE", id="att-1",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.side_effect = [_ScalarResult(None), _ScalarResult(existing)]
    out, enrich, ct = await _call_join(
        _join_data(name="New Name", goals="meet VCs"), db, _join_settings()
    )
    assert existing.ticket_type == "SPONSOR"
    assert existing.name == "New Name"
    assert existing.goals == "meet VCs"
    assert existing.magic_access_token  # generated during merge
    enrich.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_join_flow.py -k join -v`
Expected: FAIL — `auth.join` does not exist.

- [ ] **Step 3: Add the endpoint** (in `auth.py`, after `register`)

```python
@router.post("/join", response_model=Token, status_code=201)
@limiter.limit("5/minute")
async def join(
    request: Request,
    data: JoinRequest,
    db: AsyncSession = Depends(get_db),
):
    """Self-service sponsor signup via the shared invite link. The invite code
    is the gate, so this bypasses REQUIRE_TICKET_TO_REGISTER and forces
    ticket_type=SPONSOR. On success, runs the full cold-start enrichment +
    matching pipeline in the background and returns a JWT (auto-login)."""
    expected = get_settings().SPONSOR_INVITE_CODE
    if not expected or not secrets.compare_digest(data.invite_code, expected):
        raise HTTPException(status_code=403, detail="This invite link is invalid or expired.")

    if (await db.execute(select(User).where(User.email == data.email))).scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Email already registered — please log in instead.",
        )

    attendee = await _upsert_attendee_from_payload(
        db, data, force_ticket_type="SPONSOR", enforce_ticket_gate=False,
    )
    await db.flush()  # populate attendee.id

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.name,
        attendee_id=attendee.id,
    )
    db.add(user)
    await db.commit()

    # Cold start: Grid + website + AI summary + embedding + matches, detached.
    asyncio.create_task(run_full_enrichment(attendee.id))

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_join_flow.py -v`
Expected: PASS (all join tests + earlier tasks' tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_join_flow.py
git commit -m "feat: POST /auth/join sponsor self-service signup endpoint"
```

---

### Task 7: Wire the save-trigger into `PUT /auth/profile`

**Files:**
- Modify: `backend/app/api/routes/auth.py` (`update_profile`, ~line 240-280)
- Test: `backend/tests/test_join_flow.py`

- [ ] **Step 1: Write the failing test** (append)

```python
@pytest.mark.asyncio
async def test_profile_save_dispatches_refresh():
    import uuid
    aid = uuid.uuid4()
    attendee = SimpleNamespace(id=aid, embedding=[1.0], name="X")
    user = SimpleNamespace(attendee_id=aid, full_name="X")
    db = AsyncMock()
    db.get = AsyncMock(return_value=attendee)
    ct = _fake_ct()
    with patch.object(auth, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", ct), \
         patch.object(auth, "UserResponse") as UR, \
         patch("app.schemas.attendee.AttendeeResponse") as AR:
        UR.model_validate.return_value = {}
        AR.model_validate.return_value = {}
        await auth.update_profile({"goals": "new goals"}, user, db)
    refresh.assert_called_once_with(aid)
    ct.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_join_flow.py::test_profile_save_dispatches_refresh -v`
Expected: FAIL — `refresh` not called (no trigger wired yet).

- [ ] **Step 3: Add the dispatch**

In `update_profile`, after `await db.commit()` and `await db.refresh(attendee)` (auth.py:273-274), before building the response, add:

```python
    # Save triggers an immediate re-embed + match refresh (the "enrich your
    # profile to unlock better matches" loop) instead of waiting for the cron.
    asyncio.create_task(refresh_profile_matches(attendee.id))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_join_flow.py::test_profile_save_dispatches_refresh -v`
Expected: PASS

- [ ] **Step 5 (OPTIONAL — escalate to full enrichment on company/website/linkedin change):**

If the save introduces a new company, company_website, or first linkedin_url, prefer `run_full_enrichment` so the new source gets a Grid/website pass. Replace the dispatch from Step 3 with:

```python
    _escalate_fields = {"company", "company_website", "linkedin_url"}
    if _escalate_fields & set(data.keys()):
        asyncio.create_task(run_full_enrichment(attendee.id))
    else:
        asyncio.create_task(refresh_profile_matches(attendee.id))
```

This is optional; the light path is correct for typed-field edits. If you implement it, update the Step 1 test to patch `run_full_enrichment` for a company-change case, or keep the test on a `goals`-only save (which still takes the light path).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_join_flow.py
git commit -m "feat: profile save triggers immediate re-embed + match refresh"
```

---

### Task 8: Wire the save-trigger into `PATCH /matches/m/{token}/profile`

**Files:**
- Modify: `backend/app/api/routes/matches.py` (`update_profile_via_magic_link`, ~line 372-407)
- Test: `backend/tests/test_magic_profile_trigger.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_magic_profile_trigger.py
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.api.routes.matches as matches


class _ScalarResult:
    def __init__(self, row):
        self._row = row
    def scalars(self):
        return self
    def first(self):
        return self._row


@pytest.mark.asyncio
async def test_magic_profile_save_dispatches_refresh():
    aid = uuid.uuid4()
    attendee = SimpleNamespace(
        id=aid, twitter_handle=None, target_companies=None, photo_url=None,
        privacy_mode="full", linkedin_url=None, goals=None,
        magic_access_token="tok-abcdef1234567890",
    )
    db = AsyncMock()
    db.execute.return_value = _ScalarResult(attendee)
    data = SimpleNamespace(
        twitter_handle=None, target_companies="VCs in DeFi", photo_url=None,
        privacy_mode=None, linkedin_url=None, goals=None,
    )

    def _ct(coro):
        coro.close()
        return MagicMock()

    with patch.object(matches, "refresh_profile_matches", AsyncMock()) as refresh, \
         patch("asyncio.create_task", MagicMock(side_effect=_ct)):
        out = await matches.update_profile_via_magic_link(
            "tok-abcdef1234567890", data, db
        )
    assert out == {"status": "updated"}
    refresh.assert_called_once_with(aid)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_magic_profile_trigger.py -v`
Expected: FAIL — `matches.refresh_profile_matches` does not exist / not called.

- [ ] **Step 3: Add the import and the dispatch**

In `backend/app/api/routes/matches.py`:

(a) Ensure `import asyncio` is present at the top (add it if `grep -n "^import asyncio" backend/app/api/routes/matches.py` returns nothing).

(b) Add the import (near the other service imports):

```python
from app.services.profile_pipeline import refresh_profile_matches
```

(c) In `update_profile_via_magic_link`, change the end from:

```python
    await db.commit()
    return {"status": "updated"}
```

to:

```python
    await db.commit()
    # Self-fill via magic link also unlocks/refreshes matches immediately.
    asyncio.create_task(refresh_profile_matches(attendee.id))
    return {"status": "updated"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_magic_profile_trigger.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/matches.py backend/tests/test_magic_profile_trigger.py
git commit -m "feat: magic-link profile save triggers re-embed + match refresh"
```

---

### Task 9: Consolidate the Concierge save onto `refresh_profile_matches`

**Files:**
- Modify: `backend/app/api/routes/chat.py` (`_refresh_attendee_matches_bg` ~line 35-54; `save_field` add_task ~line 241)
- Test: `backend/tests/test_concierge_refresh_consolidation.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_concierge_refresh_consolidation.py
def test_concierge_uses_shared_refresh():
    import app.api.routes.chat as chat
    # The duplicated background helper is gone; the shared function is imported.
    assert hasattr(chat, "refresh_profile_matches")
    assert not hasattr(chat, "_refresh_attendee_matches_bg")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_concierge_refresh_consolidation.py -v`
Expected: FAIL — `_refresh_attendee_matches_bg` still defined.

- [ ] **Step 3: Refactor**

In `backend/app/api/routes/chat.py`:

(a) Add the import (with the other service imports):

```python
from app.services.profile_pipeline import refresh_profile_matches
```

(b) Delete the `_refresh_attendee_matches_bg` function (lines ~35-54).

(c) Change the scheduling line in `save_field` (line ~241) from:

```python
        background_tasks.add_task(_refresh_attendee_matches_bg, attendee.id)
```

to:

```python
        background_tasks.add_task(refresh_profile_matches, attendee.id)
```

(d) Remove now-unused imports in `chat.py` if they were only used by the deleted helper (grep for `MatchingEngine`, `async_session` usage in `chat.py`; remove only if no other references remain).

Note: the shared function uses `notify=False`, so a Concierge field-draft save no longer fires match notifications. This is intended (a draft save shouldn't email people) and has no production effect today (emails are gated to team-only via `EMAIL_MODE=allowlist`).

- [ ] **Step 4: Run test + full suite**

Run: `pytest tests/test_concierge_refresh_consolidation.py -v && pytest -q`
Expected: PASS; no new suite failures.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/chat.py backend/tests/test_concierge_refresh_consolidation.py
git commit -m "refactor: concierge save uses shared refresh_profile_matches"
```

---

### Task 10: Frontend API client — `joinViaInvite`

**Files:**
- Modify: `frontend/src/api/client.ts` (after `registerUser`, ~line 372)

- [ ] **Step 1: Add the function**

```typescript
export async function joinViaInvite(body: {
  invite_code: string;
  email: string;
  password: string;
  name: string;
  company?: string;
  title?: string;
  linkedin_url?: string;
  twitter_handle?: string;
  company_website?: string;
  goals?: string;
  target_companies?: string;
  interests?: string[];
  privacy_mode?: string;
}): Promise<Token> {
  const { data } = await api.post("/auth/join", body);
  return data;
}
```

- [ ] **Step 2: Verify it type-checks**

Run: `cd frontend && npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: joinViaInvite API client for sponsor signup"
```

---

### Task 11: `AuthContext.joinViaInvite` + `SponsorJoin` page

**Files:**
- Modify: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/pages/SponsorJoin.tsx`

- [ ] **Step 1: Add `joinViaInvite` to AuthContext**

In `frontend/src/context/AuthContext.tsx`:

(a) Extend the import from the client:

```typescript
import { loginUser, registerUser, getMe, api, joinViaInvite as joinViaInviteApi } from "../api/client";
```

(b) Add to the context type (next to `register: (data: RegisterData) => Promise<void>;`):

```typescript
  joinViaInvite: (data: Parameters<typeof joinViaInviteApi>[0]) => Promise<void>;
```

(c) Add a default no-op in the `createContext` default object (next to `register: async () => {},`):

```typescript
  joinViaInvite: async () => {},
```

(d) Add the callback (next to `register`):

```typescript
  const joinViaInvite = useCallback(
    async (data: Parameters<typeof joinViaInviteApi>[0]) => {
      const { access_token } = await joinViaInviteApi(data);
      api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
      const me = await getMe();
      setAuth(access_token, me);
    },
    [setAuth]
  );
```

(e) Add `joinViaInvite` to the provider `value={{ ... }}` object (next to `register,`).

- [ ] **Step 2: Read `Register.tsx` for styling parity, then create the page**

Read `frontend/src/pages/Register.tsx` first to copy its exact Tailwind classes/wrappers, then create `frontend/src/pages/SponsorJoin.tsx`. The following is the complete, functional baseline — adapt the className strings to match Register.tsx's look:

```tsx
import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function SponsorJoin() {
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const { joinViaInvite } = useAuth();
  const [form, setForm] = useState({
    name: "", email: "", password: "", company: "", title: "",
    linkedin_url: "", goals: "", target_companies: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set =
    (k: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [k]: e.target.value });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const p = form.password;
    if (p.length < 8 || !/[A-Z]/.test(p) || !/[a-z]/.test(p) || !/\d/.test(p)) {
      setError("Password needs 8+ characters with an uppercase, lowercase, and a number.");
      return;
    }
    let linkedin = form.linkedin_url.trim();
    if (linkedin && !linkedin.startsWith("http")) linkedin = `https://${linkedin}`;
    setSubmitting(true);
    try {
      await joinViaInvite({
        invite_code: code,
        email: form.email.trim().toLowerCase(),
        password: form.password,
        name: form.name.trim(),
        company: form.company.trim(),
        title: form.title.trim(),
        linkedin_url: linkedin || undefined,
        goals: form.goals.trim() || undefined,
        target_companies: form.target_companies.trim() || undefined,
      });
      navigate("/matches");
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-10">
      <h1 className="text-2xl font-semibold text-white mb-1">Join Proof of Talk</h1>
      <p className="text-sm text-gray-400 mb-6">
        Create your profile. Once you save, we’ll enrich it and surface your matches.
      </p>
      {error && (
        <div className="mb-4 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
          {error.toLowerCase().includes("already registered") && (
            <>
              {" "}
              <Link to="/login" className="underline">Log in</Link>.
            </>
          )}
        </div>
      )}
      <form onSubmit={onSubmit} className="space-y-3">
        <input required placeholder="Full name" value={form.name} onChange={set("name")} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <input required type="email" placeholder="Work email" value={form.email} onChange={set("email")} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <input required type="password" placeholder="Password" value={form.password} onChange={set("password")} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <input placeholder="Company" value={form.company} onChange={set("company")} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <input placeholder="Title" value={form.title} onChange={set("title")} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <input placeholder="LinkedIn URL" value={form.linkedin_url} onChange={set("linkedin_url")} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <textarea placeholder="What do you want to get out of Proof of Talk?" value={form.goals} onChange={set("goals")} rows={3} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <textarea placeholder="Who do you want to meet?" value={form.target_companies} onChange={set("target_companies")} rows={2} className="w-full rounded-md bg-gray-800 px-3 py-2 text-white" />
        <button type="submit" disabled={submitting} className="w-full rounded-md bg-[#E76315] px-3 py-2 font-medium text-white disabled:opacity-60">
          {submitting ? "Setting up your matches…" : "Create my profile"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2b: Type-check**

Run: `cd frontend && npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/context/AuthContext.tsx frontend/src/pages/SponsorJoin.tsx
git commit -m "feat: SponsorJoin page + AuthContext.joinViaInvite"
```

---

### Task 12: Route the page + production build

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the import and route**

In `frontend/src/App.tsx`, add the import next to the other page imports:

```typescript
import SponsorJoin from "./pages/SponsorJoin";
```

and the route inside `<Routes>` (next to the `/register` route):

```tsx
              <Route path="/join/:code" element={<SponsorJoin />} />
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds (`tsc -b && vite build` clean).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: route /join/:code to SponsorJoin page"
```

---

### Task 13: Docs + end-to-end smoke

**Files:**
- Modify: `CLAUDE.md`, `session_log.md`, `whats_next.md`, `project_state.md`

- [ ] **Step 1: Update `CLAUDE.md`**

Under "Environment Variables", add a line for `SPONSOR_INVITE_CODE` (blank = off; shared `/join/<code>` link; rotating revokes). Under "Key Design Decisions" (near the magic-link section), add a short "Sponsor self-service invite link" paragraph describing `/join/:code` → `POST /auth/join` → `run_full_enrichment`, and that every profile save now fires `refresh_profile_matches`.

- [ ] **Step 2: End-to-end smoke (local)**

```bash
# Backend with a temporary code
cd backend && source .venv/bin/activate
SPONSOR_INVITE_CODE=test-smoke-code uvicorn app.main:app --reload --port 8000
```

In another shell:

```bash
# valid code → 201 + token. Use the operator-provided real smoke profile:
# Precious Zuze, zuzvaida@gmail.com, https://www.linkedin.com/in/precious-zuze-a60b05202/
curl -s -X POST localhost:8000/api/v1/auth/join -H 'Content-Type: application/json' \
  -d '{"invite_code":"test-smoke-code","email":"zuzvaida@gmail.com","password":"Strong1pass","name":"Precious Zuze","linkedin_url":"https://www.linkedin.com/in/precious-zuze-a60b05202/","goals":"Smoke-test the sponsor self-service join flow"}' | head -c 300; echo
# wrong code → 403
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/api/v1/auth/join \
  -H 'Content-Type: application/json' \
  -d '{"invite_code":"nope","email":"x@example.com","password":"Strong1pass","name":"X"}'
```

Expected: first returns `{"access_token": "...", "token_type":"bearer"}`; second prints `403`.
Then verify in the DB that `smoke@example.com` exists as an attendee with `ticket_type=SPONSOR` and a `magic_access_token`, and that an `enriched_profile`/`embedding`/matches appear within ~30s (background pipeline). **Delete the smoke row afterward.**

Frontend smoke: `cd frontend && npm run dev`, open `http://localhost:5173/join/test-smoke-code`, fill the form, submit, confirm redirect to `/matches`. Open `/join/wrong-code`, submit, confirm the invalid-link error.

- [ ] **Step 3: Update living docs**

- `session_log.md`: append `## 2026-05-22 — [sponsor-invite-link] Sponsor self-service /join + universal save-trigger` with bullets.
- `whats_next.md`: move this item to Done; add a Now item "Set production `SPONSOR_INVITE_CODE` in Railway + share the link" and "Run a LinkedIn scrape pass to pick up sponsor joiners".
- `project_state.md`: add to What's Working.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md session_log.md whats_next.md project_state.md
git commit -m "docs: sponsor self-service invite link + universal save-trigger"
```

---

## Self-Review

**Spec coverage:**
- Shared `/join/<code>` link, off by default → Tasks 3 (config), 6 (endpoint), 12 (route). ✅
- `POST /auth/join`, ticket-gate bypass, force SPONSOR, constant-time code, JWT auto-login → Tasks 4, 6. ✅
- `run_full_enrichment` (Grid + website + embed + matches) on cold-start join → Tasks 2, 6. ✅
- LinkedIn queued (no code — joiner with linkedin_url appears in pending count) → documented in spec/Task 13; no task needed. ✅
- Universal save-trigger `refresh_profile_matches` on Profile, magic-link, Concierge, register → Tasks 1, 5, 7, 8, 9. ✅
- Frontend page + API + context → Tasks 10, 11, 12. ✅
- Docs (CLAUDE.md, .env.example, living docs) → Tasks 3, 13. ✅
- Tests for all backend logic → Tasks 1, 2, 4, 5, 6, 7, 8, 9. ✅

**Placeholder scan:** none — every step has complete code/commands.

**Type/name consistency:** `refresh_profile_matches(attendee_id)` and `run_full_enrichment(attendee_id)` used identically across Tasks 1, 2, 5, 6, 7, 8, 9. `generate_matches_for_attendee(aid, top_k=10, notify=False)` matches the engine signature. `_upsert_attendee_from_payload(db, data, *, force_ticket_type, enforce_ticket_gate)` used consistently in Tasks 5 and 6. `joinViaInvite` consistent across client (Task 10), context + page (Task 11).

**Note on the optional escalation (Task 7 Step 5):** clearly marked optional; the light path is the default and is fully tested.
