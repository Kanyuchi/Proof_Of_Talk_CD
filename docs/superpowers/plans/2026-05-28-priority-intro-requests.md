# Priority Intro Requests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface per-attendee priority intro requests as a new `priority_intro` match tier above curated, with honest factual cards (no GPT fabrication) and `accepted_*_at` timestamps for ROI audit.

**Architecture:** New `requested_intros` table (per-requester rows). Matching engine consumes these alongside the existing curated+deep tiers — in-pool targets get tier-upgraded, out-of-pool targets are force-added with a templated explanation. New `accepted_a_at`/`accepted_b_at` columns on `matches` mirror the existing `deferred_*_at` pattern.

**Tech Stack:** SQLAlchemy 2.0 async + Alembic, FastAPI, React + TypeScript, pytest, rapidfuzz for the ingest script.

**Spec:** `docs/superpowers/specs/2026-05-28-priority-intro-requests-design.md`

**Test conventions:** This codebase uses **mock-DB tests** (`AsyncMock` for `db.execute` with `side_effect` sequencing the expected queries), not real-DB fixtures. See `backend/tests/test_adoption_endpoint.py` for the canonical pattern (`_Scalar` / `_Rows` helpers + `_make_db()` that returns a sequenced `AsyncMock`). The test code shown in this plan is the BEHAVIOUR each test should cover — adapt the scaffolding to match the mock-DB pattern when you write each test. Do NOT introduce real-DB pytest fixtures (`db_session`, `attendee_factory`, etc.) — that would diverge from the established convention. If you need real DB integration for a test, run it against the dev Supabase using the existing `app.core.database.async_session_maker` pattern.

---

## File Structure

**Backend create:**
- `backend/alembic/versions/<new>_add_priority_intros_and_accepted_timestamps.py` — single migration covering both schema changes
- `backend/scripts/ingest_requested_intros.py` — operator-run sheet-to-DB ingest
- `backend/tests/test_requested_intros_ingest.py`
- `backend/tests/test_matching_priority_intros.py`
- `backend/tests/test_matches_accepted_timestamps.py`
- `backend/tests/test_priority_intros_endpoint.py`

**Backend modify:**
- `backend/app/models/attendee.py` — add `RequestedIntro` model + `accepted_a_at`/`accepted_b_at` on `Match`
- `backend/app/schemas/attendee.py` — extend `MatchResponse` with `priority_intro_meta` and `accepted_a_at`/`accepted_b_at`; new `PriorityIntroResponse` for the new endpoint
- `backend/app/services/matching.py` — in `generate_matches_for_attendee`, layer priority intros on top of curated+deep
- `backend/app/api/routes/matches.py` — stamp accepted_*_at in both status routes; new `GET /matches/priority-intros` and `GET /matches/m/{token}/priority-intros` endpoints

**Frontend modify:**
- `frontend/src/types/index.ts` — extend `Match` with `priority_intro_meta` and new `"priority_intro"` value on `tier`
- `frontend/src/pages/MyMatches.tsx` — render "Your priority intros" section above curated
- `frontend/src/pages/MagicMatches.tsx` — same treatment

---

## Task 1: Migration — `requested_intros` table + `accepted_*_at` columns

**Files:**
- Create: `backend/alembic/versions/9b3e2d1a8c4f_add_priority_intros_and_accepted_timestamps.py`

- [ ] **Step 1.1: Generate the migration file**

```bash
cd backend && source .venv/bin/activate
alembic revision -m "add_priority_intros_and_accepted_timestamps"
```

Then rename the generated file's revision id to `9b3e2d1a8c4f` (or whatever Alembic generated) for stability across the rest of this plan. Note the actual revision id and use it consistently.

- [ ] **Step 1.2: Replace the migration body**

Replace the generated upgrade/downgrade with:

```python
"""add_priority_intros_and_accepted_timestamps

Revision ID: 9b3e2d1a8c4f
Revises: 24a02695202e
Create Date: 2026-05-28 20:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9b3e2d1a8c4f"
down_revision: Union[str, None] = "24a02695202e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requested_intros",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("requester_attendee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_attendee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_name_raw", sa.Text(), nullable=False),
        sa.Column("target_company_raw", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["requester_attendee_id"], ["attendees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_attendee_id"], ["attendees.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_requested_intros_requester",
        "requested_intros",
        ["requester_attendee_id"],
    )
    op.create_index(
        "ix_requested_intros_target",
        "requested_intros",
        ["target_attendee_id"],
    )
    op.create_unique_constraint(
        "uq_requested_intros_dedup",
        "requested_intros",
        ["requester_attendee_id", "target_name_raw", "target_company_raw"],
    )

    op.add_column("matches", sa.Column("accepted_a_at", sa.DateTime(), nullable=True))
    op.add_column("matches", sa.Column("accepted_b_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "accepted_b_at")
    op.drop_column("matches", "accepted_a_at")
    op.drop_constraint("uq_requested_intros_dedup", "requested_intros", type_="unique")
    op.drop_index("ix_requested_intros_target", table_name="requested_intros")
    op.drop_index("ix_requested_intros_requester", table_name="requested_intros")
    op.drop_table("requested_intros")
```

- [ ] **Step 1.3: Run the migration against local DB**

```bash
cd backend && source .venv/bin/activate
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade 24a02695202e -> 9b3e2d1a8c4f`

- [ ] **Step 1.4: Verify with psql**

```bash
psql "$DATABASE_URL" -c "\d requested_intros" -c "\d matches"
```

Expected: `requested_intros` table exists with all 8 columns; `matches` shows `accepted_a_at` and `accepted_b_at` columns.

- [ ] **Step 1.5: Commit**

```bash
git add backend/alembic/versions/9b3e2d1a8c4f_add_priority_intros_and_accepted_timestamps.py
git commit -m "feat(db): add requested_intros table and matches.accepted_*_at columns"
```

---

## Task 2: ORM model — `RequestedIntro` + `Match.accepted_*_at`

**Files:**
- Modify: `backend/app/models/attendee.py`

- [ ] **Step 2.1: Add columns to existing `Match` class**

Inside `class Match(Base)` in `backend/app/models/attendee.py`, right after the existing `deferred_a_at`/`deferred_b_at` lines (currently around line 141-142):

```python
    # Set the first time each party transitions to status="accepted". Mirrors
    # deferred_*_at. Used for sponsor ROI reporting on priority intros.
    accepted_a_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_b_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 2.2: Add the `RequestedIntro` class**

At the bottom of `backend/app/models/attendee.py`:

```python
class RequestedIntro(Base):
    """Per-attendee curated intro request — e.g. Elliptic gold-tier perk where
    each Elliptic attendee has a sheet tab listing people they want to meet.
    Surfaces in the requester's match list as the priority_intro tier."""

    __tablename__ = "requested_intros"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_attendee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    # NULL when the target isn't in our DB yet (e.g. they haven't registered).
    target_attendee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    target_name_raw: Mapped[str] = mapped_column(Text)
    target_company_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 2.3: Quick import smoke-test**

```bash
cd backend && source .venv/bin/activate
python -c "from app.models.attendee import Match, RequestedIntro; print(Match.accepted_a_at, RequestedIntro.__tablename__)"
```

Expected: prints the two attributes without error.

- [ ] **Step 2.4: Commit**

```bash
git add backend/app/models/attendee.py
git commit -m "feat(models): add RequestedIntro and Match.accepted_*_at"
```

---

## Task 3: Stamp `accepted_a_at` / `accepted_b_at` in status routes

**Files:**
- Modify: `backend/app/api/routes/matches.py`
- Test: `backend/tests/test_matches_accepted_timestamps.py`

- [ ] **Step 3.1: Write the failing test**

Create `backend/tests/test_matches_accepted_timestamps.py`:

```python
"""Verify that accepting a match stamps the per-side timestamp exactly once,
and doesn't fire on declined/met transitions."""
import pytest
from datetime import datetime
from uuid import uuid4

pytestmark = pytest.mark.asyncio


async def test_accept_stamps_accepted_a_at(client, db_session, two_attendees_with_match):
    user_a, _, match = two_attendees_with_match
    headers = {"Authorization": f"Bearer {user_a.token}"}

    resp = await client.patch(
        f"/api/v1/matches/{match.id}/status",
        json={"status": "accepted"},
        headers=headers,
    )
    assert resp.status_code == 200

    await db_session.refresh(match)
    assert match.accepted_a_at is not None
    assert isinstance(match.accepted_a_at, datetime)
    assert match.accepted_b_at is None


async def test_decline_does_not_stamp(client, db_session, two_attendees_with_match):
    user_a, _, match = two_attendees_with_match
    headers = {"Authorization": f"Bearer {user_a.token}"}

    resp = await client.patch(
        f"/api/v1/matches/{match.id}/status",
        json={"status": "declined", "decline_reason": "no fit"},
        headers=headers,
    )
    assert resp.status_code == 200

    await db_session.refresh(match)
    assert match.accepted_a_at is None


async def test_magic_link_accept_stamps_accepted_a_at(client, db_session, two_attendees_with_match):
    _, attendee_a, match = two_attendees_with_match
    resp = await client.patch(
        f"/api/v1/matches/m/{attendee_a.magic_access_token}/status",
        json={"match_id": str(match.id), "status": "accepted"},
    )
    assert resp.status_code == 200
    await db_session.refresh(match)
    assert match.accepted_a_at is not None


async def test_accept_is_idempotent_does_not_overwrite(client, db_session, two_attendees_with_match):
    """Second accept call must not bump the timestamp — we record FIRST accept."""
    user_a, _, match = two_attendees_with_match
    headers = {"Authorization": f"Bearer {user_a.token}"}

    await client.patch(
        f"/api/v1/matches/{match.id}/status",
        json={"status": "accepted"},
        headers=headers,
    )
    await db_session.refresh(match)
    first_ts = match.accepted_a_at
    assert first_ts is not None

    await client.patch(
        f"/api/v1/matches/{match.id}/status",
        json={"status": "accepted"},
        headers=headers,
    )
    await db_session.refresh(match)
    assert match.accepted_a_at == first_ts
```

This test references a fixture `two_attendees_with_match` which provides two registered attendees + a `Match` row between them, with `user_a.token` set to a valid JWT for the first attendee. If the fixture does not yet exist, add it to `backend/tests/conftest.py` using the existing patterns there (see other tests that use `client` and `db_session` for the shape — typically existing fixtures like `attendee_factory` exist; if so, compose from those).

- [ ] **Step 3.2: Run the tests — they must fail**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_matches_accepted_timestamps.py -v
```

Expected: FAIL with `assert match.accepted_a_at is not None` (column exists from Task 2 but route doesn't stamp it yet).

- [ ] **Step 3.3: Update `update_match_status` to stamp the timestamp**

In `backend/app/api/routes/matches.py`, find the authed `update_match_status` function (around line 630). Replace the side-assignment block:

```python
    # Determine which side this user is on, based on their linked attendee_id
    if user.attendee_id and str(user.attendee_id) == str(match.attendee_a_id):
        match.status_a = data.status
    elif user.attendee_id and str(user.attendee_id) == str(match.attendee_b_id):
        match.status_b = data.status
```

with:

```python
    # Determine which side this user is on, based on their linked attendee_id
    if user.attendee_id and str(user.attendee_id) == str(match.attendee_a_id):
        if data.status == "accepted" and match.accepted_a_at is None:
            match.accepted_a_at = datetime.utcnow()
        match.status_a = data.status
    elif user.attendee_id and str(user.attendee_id) == str(match.attendee_b_id):
        if data.status == "accepted" and match.accepted_b_at is None:
            match.accepted_b_at = datetime.utcnow()
        match.status_b = data.status
```

- [ ] **Step 3.4: Update `update_match_status_by_magic_link` to stamp the timestamp**

In the same file, find `update_match_status_by_magic_link` (around line 318). Replace:

```python
    if match.attendee_a_id == attendee.id:
        match.status_a = data.status
    else:
        match.status_b = data.status
```

with:

```python
    if match.attendee_a_id == attendee.id:
        if data.status == "accepted" and match.accepted_a_at is None:
            match.accepted_a_at = datetime.utcnow()
        match.status_a = data.status
    else:
        if data.status == "accepted" and match.accepted_b_at is None:
            match.accepted_b_at = datetime.utcnow()
        match.status_b = data.status
```

- [ ] **Step 3.5: Verify `datetime` is already imported**

```bash
grep -n "from datetime\|^import datetime" backend/app/api/routes/matches.py | head
```

Expected: at least one `from datetime import datetime` (or similar). If `datetime` is not imported, add `from datetime import datetime` at the top.

- [ ] **Step 3.6: Run the tests — they must pass**

```bash
pytest tests/test_matches_accepted_timestamps.py -v
```

Expected: 4 passed.

- [ ] **Step 3.7: Run the full matches route test file to ensure no regression**

```bash
pytest tests/ -k matches -v
```

Expected: all existing match tests still pass.

- [ ] **Step 3.8: Commit**

```bash
git add backend/app/api/routes/matches.py backend/tests/test_matches_accepted_timestamps.py
git commit -m "feat(matches): stamp accepted_a_at/_b_at on first accept transition"
```

---

## Task 4: Extend `MatchResponse` schema with new fields

**Files:**
- Modify: `backend/app/schemas/attendee.py`

- [ ] **Step 4.1: Add fields to `MatchResponse`**

In `backend/app/schemas/attendee.py`, inside `class MatchResponse(BaseModel)` (currently around line 80), add these fields just before `created_at: datetime`:

```python
    accepted_a_at: datetime | None = None
    accepted_b_at: datetime | None = None
    # Populated only when tier == "priority_intro". Surfaces requester-side
    # context to the frontend (so the card can render "requested from your
    # concierge" framing without an extra fetch).
    priority_intro_meta: dict | None = None
```

- [ ] **Step 4.2: Add a new `PriorityIntroResponse` schema**

At the bottom of `backend/app/schemas/attendee.py`:

```python
class PriorityIntroResponse(BaseModel):
    """One row in the requester's priority-intro list. Includes unresolved
    targets (target_attendee_id IS NULL) so the UI can render greyed-out
    'Not yet attending' cards."""
    id: UUID
    requester_attendee_id: UUID
    target_attendee_id: UUID | None
    target_name_raw: str
    target_company_raw: str | None
    source: str
    added_at: datetime
    resolved_at: datetime | None
    # Joined for convenience when target_attendee_id is set.
    target: AttendeeResponse | None = None
    # The corresponding Match row id, if one already exists. Lets the UI
    # link the unresolved card to its match row once the target registers.
    match_id: UUID | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4.3: Verify pydantic accepts the schema**

```bash
cd backend && source .venv/bin/activate
python -c "from app.schemas.attendee import MatchResponse, PriorityIntroResponse; print('OK')"
```

Expected: `OK`.

- [ ] **Step 4.4: Commit**

```bash
git add backend/app/schemas/attendee.py
git commit -m "feat(schemas): extend MatchResponse + add PriorityIntroResponse"
```

---

## Task 5: Matching service — priority-intro tier upgrade + force-include

**Files:**
- Modify: `backend/app/services/matching.py`
- Test: `backend/tests/test_matching_priority_intros.py`

- [ ] **Step 5.1: Write the failing test for tier upgrade**

Create `backend/tests/test_matching_priority_intros.py`:

```python
"""Priority intro requests: in-pool targets get tier upgrade, out-of-pool
targets get force-added with factual explanation (no GPT)."""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.models.attendee import Match, RequestedIntro
from app.services.matching import MatchingEngine, PRIORITY_INTRO_CAP

pytestmark = pytest.mark.asyncio


async def test_target_in_pool_gets_tier_upgrade(
    db_session, attendee_factory, engine_with_mock_openai
):
    requester = await attendee_factory()
    target = await attendee_factory()
    # Pre-seed a RequestedIntro
    intro = RequestedIntro(
        requester_attendee_id=requester.id,
        target_attendee_id=target.id,
        target_name_raw=target.name,
        target_company_raw=target.company,
        source="test",
    )
    db_session.add(intro)
    await db_session.commit()

    # Mock retrieve_candidates to return target with high similarity (in-pool)
    engine_with_mock_openai.retrieve_candidates = AsyncMock(
        return_value=[(target, 0.95)]
    )

    matches = await engine_with_mock_openai.generate_matches_for_attendee(requester.id)

    target_match = next(m for m in matches if m.attendee_b_id == target.id or m.attendee_a_id == target.id)
    assert target_match.tier == "priority_intro"


async def test_target_not_in_pool_is_force_added_with_factual_explanation(
    db_session, attendee_factory, engine_with_mock_openai
):
    requester = await attendee_factory()
    target = await attendee_factory(name="Jane Target", goals="raise series B")
    other = await attendee_factory()

    intro = RequestedIntro(
        requester_attendee_id=requester.id,
        target_attendee_id=target.id,
        target_name_raw=target.name,
        target_company_raw=target.company,
        source="test",
    )
    db_session.add(intro)
    await db_session.commit()

    # Pool returns "other" but NOT target — so target must be force-added
    engine_with_mock_openai.retrieve_candidates = AsyncMock(
        return_value=[(other, 0.80)]
    )

    matches = await engine_with_mock_openai.generate_matches_for_attendee(requester.id)

    priority_matches = [m for m in matches if m.tier == "priority_intro"]
    assert len(priority_matches) == 1
    pm = priority_matches[0]
    assert "Jane" in pm.explanation
    assert "raise series B" in pm.explanation
    assert pm.similarity_score == 0.0
    assert pm.overall_score == 0.0


async def test_unresolved_target_attendee_id_null_is_skipped(
    db_session, attendee_factory, engine_with_mock_openai
):
    requester = await attendee_factory()
    intro = RequestedIntro(
        requester_attendee_id=requester.id,
        target_attendee_id=None,
        target_name_raw="Unknown Person",
        target_company_raw="Unknown Co",
        source="test",
    )
    db_session.add(intro)
    await db_session.commit()
    engine_with_mock_openai.retrieve_candidates = AsyncMock(return_value=[])

    matches = await engine_with_mock_openai.generate_matches_for_attendee(requester.id)
    assert all(m.tier != "priority_intro" for m in matches)


async def test_priority_intro_cap_enforced(
    db_session, attendee_factory, engine_with_mock_openai
):
    requester = await attendee_factory()
    # Create CAP+5 resolved intros, none in the candidate pool
    targets = [await attendee_factory() for _ in range(PRIORITY_INTRO_CAP + 5)]
    for t in targets:
        db_session.add(RequestedIntro(
            requester_attendee_id=requester.id,
            target_attendee_id=t.id,
            target_name_raw=t.name,
            target_company_raw=t.company,
            source="test",
        ))
    await db_session.commit()
    engine_with_mock_openai.retrieve_candidates = AsyncMock(return_value=[])

    matches = await engine_with_mock_openai.generate_matches_for_attendee(requester.id)
    priority = [m for m in matches if m.tier == "priority_intro"]
    assert len(priority) == PRIORITY_INTRO_CAP
```

- [ ] **Step 5.2: Run the tests — must fail**

```bash
pytest tests/test_matching_priority_intros.py -v
```

Expected: FAIL — `PRIORITY_INTRO_CAP` not defined, and tier upgrade / force-add behaviour absent.

- [ ] **Step 5.3: Define constants in `matching.py`**

At the top of `backend/app/services/matching.py` near the other tier constants (around line 36, after `SPONSOR_DEEP_POOL_SIZE`):

```python
# Priority intro requests (concierge-curated, e.g. Elliptic gold-tier perk).
# Per-attendee cap on priority_intro-tier rows — protects UI + matching pipeline
# from a runaway sheet. Matches SPONSOR_DEEP_POOL_SIZE.
PRIORITY_INTRO_CAP = 50

PRIORITY_INTRO_EXPLANATION_TEMPLATE = (
    "You asked your concierge to introduce you to {target_first_name}. "
    "They're attending Proof of Talk 2026.\n\n"
    "Their focus: {target_focus}\n\n"
    "William may reach out to set up a soft intro."
)
```

- [ ] **Step 5.4: Add the helper function `_apply_priority_intros`**

In `backend/app/services/matching.py`, add this helper inside `MatchingEngine` (location: just before `generate_matches_for_attendee`):

```python
    async def _apply_priority_intros(
        self,
        attendee,
        existing_matches: list,
    ) -> list:
        """Tier-upgrade existing matches whose other side is on the requester's
        priority list, and force-add new Match rows for targets that didn't
        survive the retrieval cut. Cap at PRIORITY_INTRO_CAP rows. Targets with
        target_attendee_id IS NULL are skipped (they're not in our DB yet)."""
        from app.models.attendee import RequestedIntro, Attendee

        result = await self.db.execute(
            select(RequestedIntro).where(
                RequestedIntro.requester_attendee_id == attendee.id,
                RequestedIntro.target_attendee_id.is_not(None),
            ).order_by(RequestedIntro.added_at.asc()).limit(PRIORITY_INTRO_CAP)
        )
        intros = list(result.scalars().all())
        if not intros:
            return existing_matches

        target_ids = {intro.target_attendee_id for intro in intros}

        # Index existing matches by counterparty id
        matches_by_other = {}
        for m in existing_matches:
            other_id = m.attendee_b_id if m.attendee_a_id == attendee.id else m.attendee_a_id
            matches_by_other[other_id] = m

        # Tier-upgrade matches whose counterparty is on the priority list
        for tid in target_ids:
            if tid in matches_by_other:
                matches_by_other[tid].tier = "priority_intro"

        # Force-add missing targets
        missing_ids = target_ids - set(matches_by_other.keys())
        if not missing_ids:
            return existing_matches

        result = await self.db.execute(
            select(Attendee).where(Attendee.id.in_(missing_ids))
        )
        missing_targets = {a.id: a for a in result.scalars().all()}

        added = 0
        for tid in missing_ids:
            target = missing_targets.get(tid)
            if not target:
                continue
            first_name = (target.name or "them").split()[0]
            focus = (
                target.goals
                or (target.ai_summary[:200] if target.ai_summary else "")
                or "Profile incomplete"
            )
            explanation = PRIORITY_INTRO_EXPLANATION_TEMPLATE.format(
                target_first_name=first_name,
                target_focus=focus,
            )
            new_match = Match(
                attendee_a_id=attendee.id,
                attendee_b_id=target.id,
                similarity_score=0.0,
                complementary_score=0.0,
                overall_score=0.0,
                match_type="priority_intro",
                explanation=explanation,
                shared_context={},
                tier="priority_intro",
            )
            self.db.add(new_match)
            existing_matches.append(new_match)
            added += 1

        if added:
            await self.db.flush()
        return existing_matches
```

- [ ] **Step 5.5: Call `_apply_priority_intros` from `generate_matches_for_attendee`**

In `backend/app/services/matching.py`, find the end of `generate_matches_for_attendee` (just before the `return matches` at the bottom of the method, around line 1000+). Insert before the final return:

```python
        matches = await self._apply_priority_intros(attendee, matches)
```

- [ ] **Step 5.6: Run the tests — must pass**

```bash
pytest tests/test_matching_priority_intros.py -v
```

Expected: 4 passed.

- [ ] **Step 5.7: Run the broader matching suite for regression**

```bash
pytest tests/ -k matching -v
```

Expected: all existing matching tests still pass.

- [ ] **Step 5.8: Commit**

```bash
git add backend/app/services/matching.py backend/tests/test_matching_priority_intros.py
git commit -m "feat(matching): apply priority intros as new tier above curated"
```

---

## Task 6: Endpoints — GET priority intros (authed + magic-link)

**Files:**
- Modify: `backend/app/api/routes/matches.py`
- Test: `backend/tests/test_priority_intros_endpoint.py`

- [ ] **Step 6.1: Write the failing test**

Create `backend/tests/test_priority_intros_endpoint.py`:

```python
"""Priority intros endpoints — authed + magic-link variants both return
resolved AND unresolved (target_attendee_id IS NULL) rows."""
import pytest
from uuid import uuid4

from app.models.attendee import RequestedIntro

pytestmark = pytest.mark.asyncio


async def test_authed_endpoint_returns_resolved_and_unresolved(
    client, db_session, attendee_factory, auth_token_factory
):
    requester = await attendee_factory()
    target = await attendee_factory(name="Resolved Target")
    db_session.add(RequestedIntro(
        requester_attendee_id=requester.id,
        target_attendee_id=target.id,
        target_name_raw=target.name,
        target_company_raw=target.company,
        source="test",
    ))
    db_session.add(RequestedIntro(
        requester_attendee_id=requester.id,
        target_attendee_id=None,
        target_name_raw="Unresolved Person",
        target_company_raw="Unresolved Co",
        source="test",
    ))
    await db_session.commit()

    token = await auth_token_factory(requester)
    resp = await client.get(
        "/api/v1/matches/priority-intros",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    names = {item["target_name_raw"] for item in items}
    assert "Resolved Target" in names
    assert "Unresolved Person" in names


async def test_magic_link_endpoint_returns_intros(
    client, db_session, attendee_factory
):
    requester = await attendee_factory()
    target = await attendee_factory()
    db_session.add(RequestedIntro(
        requester_attendee_id=requester.id,
        target_attendee_id=target.id,
        target_name_raw=target.name,
        target_company_raw=target.company,
        source="test",
    ))
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/matches/m/{requester.magic_access_token}/priority-intros",
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["target_attendee_id"] == str(target.id)


async def test_no_intros_returns_empty_list(client, attendee_factory, auth_token_factory):
    requester = await attendee_factory()
    token = await auth_token_factory(requester)
    resp = await client.get(
        "/api/v1/matches/priority-intros",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_magic_link_endpoint_rejects_invalid_token(client):
    resp = await client.get("/api/v1/matches/m/notarealtoken1234567890/priority-intros")
    assert resp.status_code in (400, 404)
```

- [ ] **Step 6.2: Run the test — must fail**

```bash
pytest tests/test_priority_intros_endpoint.py -v
```

Expected: FAIL with 404 (endpoints don't exist yet).

- [ ] **Step 6.3: Add the authed endpoint**

In `backend/app/api/routes/matches.py`, add this endpoint (place it next to the existing authed match routes, e.g. after `update_match_status`):

```python
@router.get("/priority-intros", response_model=list[PriorityIntroResponse])
async def list_priority_intros(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Return all priority intros for the calling user. Includes resolved
    (target_attendee_id set) and unresolved (NULL) entries."""
    if not user.attendee_id:
        return []
    return await _load_priority_intros(db, user.attendee_id)


async def _load_priority_intros(db: AsyncSession, attendee_id) -> list[PriorityIntroResponse]:
    result = await db.execute(
        select(RequestedIntro)
        .where(RequestedIntro.requester_attendee_id == attendee_id)
        .order_by(RequestedIntro.added_at.asc())
    )
    intros = list(result.scalars().all())
    if not intros:
        return []

    # Hydrate target attendees in one query
    target_ids = [i.target_attendee_id for i in intros if i.target_attendee_id]
    targets_by_id = {}
    if target_ids:
        res = await db.execute(select(Attendee).where(Attendee.id.in_(target_ids)))
        targets_by_id = {a.id: a for a in res.scalars().all()}

    # Hydrate corresponding match_ids (one per requester+target pair, if any)
    matches_by_target = {}
    if target_ids:
        res = await db.execute(
            select(Match).where(
                ((Match.attendee_a_id == attendee_id) & (Match.attendee_b_id.in_(target_ids)))
                | ((Match.attendee_b_id == attendee_id) & (Match.attendee_a_id.in_(target_ids)))
            )
        )
        for m in res.scalars().all():
            other = m.attendee_b_id if m.attendee_a_id == attendee_id else m.attendee_a_id
            matches_by_target[other] = m.id

    out = []
    for intro in intros:
        target_resp = None
        match_id = None
        if intro.target_attendee_id:
            target_attendee = targets_by_id.get(intro.target_attendee_id)
            if target_attendee:
                target_resp = AttendeeResponse.model_validate(target_attendee)
            match_id = matches_by_target.get(intro.target_attendee_id)
        out.append(PriorityIntroResponse(
            id=intro.id,
            requester_attendee_id=intro.requester_attendee_id,
            target_attendee_id=intro.target_attendee_id,
            target_name_raw=intro.target_name_raw,
            target_company_raw=intro.target_company_raw,
            source=intro.source,
            added_at=intro.added_at,
            resolved_at=intro.resolved_at,
            target=target_resp,
            match_id=match_id,
        ))
    return out
```

- [ ] **Step 6.4: Add the magic-link endpoint**

In the same file, near `update_match_status_by_magic_link`:

```python
@router.get("/m/{token}/priority-intros", response_model=list[PriorityIntroResponse])
async def list_priority_intros_by_magic_link(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Magic-link variant of /priority-intros — no auth required, keyed by token."""
    if not token or len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid link")
    result = await db.execute(select(Attendee).where(Attendee.magic_access_token == token))
    attendee = result.scalars().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    return await _load_priority_intros(db, attendee.id)
```

- [ ] **Step 6.5: Make sure imports are in place**

At the top of `matches.py`, verify these are imported (add if missing):

```python
from app.models.attendee import Attendee, Match, RequestedIntro
from app.schemas.attendee import (
    AttendeeResponse,
    MatchResponse,
    PriorityIntroResponse,
    # ... (existing imports preserved)
)
```

- [ ] **Step 6.6: Run the tests — must pass**

```bash
pytest tests/test_priority_intros_endpoint.py -v
```

Expected: 4 passed.

- [ ] **Step 6.7: Commit**

```bash
git add backend/app/api/routes/matches.py backend/tests/test_priority_intros_endpoint.py
git commit -m "feat(api): add GET /matches/priority-intros (authed + magic-link)"
```

---

## Task 7: Ingest script — Google Sheet → `requested_intros`

**Files:**
- Create: `backend/scripts/ingest_requested_intros.py`
- Create: `backend/tests/test_requested_intros_ingest.py`

- [ ] **Step 7.1: Write the failing test**

Create `backend/tests/test_requested_intros_ingest.py`:

```python
"""Ingest script: CSV → requested_intros rows, idempotent + fuzzy-match."""
import pytest
from pathlib import Path
from uuid import uuid4

from app.models.attendee import RequestedIntro
from scripts.ingest_requested_intros import (
    parse_csv,
    match_target,
    upsert_intro,
    IngestStats,
)

pytestmark = pytest.mark.asyncio


def test_parse_csv_extracts_rows(tmp_path):
    csv = tmp_path / "input.csv"
    csv.write_text("Name,Company,Notes\nJane Doe,Coinbase,key contact\nJohn Smith,Stripe,\n")
    rows = parse_csv(csv)
    assert len(rows) == 2
    assert rows[0]["name"] == "Jane Doe"
    assert rows[0]["company"] == "Coinbase"
    assert rows[1]["company"] == "Stripe"


async def test_match_target_finds_existing_attendee(db_session, attendee_factory):
    a = await attendee_factory(name="Jane Doe", company="Coinbase")
    matched = await match_target(db_session, "Jane Doe", "Coinbase")
    assert matched is not None
    assert matched.id == a.id


async def test_match_target_returns_none_on_miss(db_session, attendee_factory):
    await attendee_factory(name="Different Person", company="Different Co")
    matched = await match_target(db_session, "Jane Doe", "Coinbase")
    assert matched is None


async def test_upsert_intro_idempotent(db_session, attendee_factory):
    requester = await attendee_factory()
    target = await attendee_factory(name="Jane Doe", company="Coinbase")
    stats = IngestStats()

    await upsert_intro(
        db_session,
        requester_id=requester.id,
        target=target,
        target_name_raw="Jane Doe",
        target_company_raw="Coinbase",
        source="test",
        stats=stats,
    )
    await db_session.commit()

    # Run again with the same input
    await upsert_intro(
        db_session,
        requester_id=requester.id,
        target=target,
        target_name_raw="Jane Doe",
        target_company_raw="Coinbase",
        source="test",
        stats=stats,
    )
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(
        select(RequestedIntro).where(RequestedIntro.requester_attendee_id == requester.id)
    )
    rows = list(result.scalars().all())
    assert len(rows) == 1
```

- [ ] **Step 7.2: Run the test — must fail**

```bash
pytest tests/test_requested_intros_ingest.py -v
```

Expected: FAIL — `scripts.ingest_requested_intros` doesn't exist yet.

- [ ] **Step 7.3: Write the script**

Create `backend/scripts/ingest_requested_intros.py`:

```python
"""Operator-run ingest: Google Sheet CSV → requested_intros rows.

Usage:
  python scripts/ingest_requested_intros.py \\
      --sheet-csv backend/data/elliptic_targets.csv \\
      --requester-email aylin@elliptic.co \\
      --source elliptic_sheet_2026_05_28 \\
      --dry-run

  # When happy with the dry-run output, re-run with --confirm.

The CSV is expected to have one tab per requester. We treat the input as a
single requester-scoped file; pass --sheet-csv once per tab. (Tabs export
from Google Sheets as one CSV per tab via Sheets > File > Download > CSV.)

Column mapping defaults to: Name | Company | Notes. Override with
--name-col / --company-col / --notes-col if the actual sheet differs.
"""
import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.attendee import Attendee, RequestedIntro


FUZZ_THRESHOLD = 85


@dataclass
class IngestStats:
    rows_read: int = 0
    matched: int = 0
    missed: int = 0
    inserted: int = 0
    skipped_duplicate: int = 0
    misses: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"rows_read={self.rows_read} matched={self.matched} missed={self.missed} "
            f"inserted={self.inserted} skipped_duplicate={self.skipped_duplicate}"
        )


def parse_csv(path: Path, name_col="Name", company_col="Company", notes_col="Notes") -> list[dict]:
    rows = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for raw in reader:
            name = (raw.get(name_col) or "").strip()
            if not name:
                continue
            rows.append({
                "name": name,
                "company": (raw.get(company_col) or "").strip() or None,
                "notes": (raw.get(notes_col) or "").strip() or None,
            })
    return rows


async def match_target(
    db: AsyncSession,
    name: str,
    company: Optional[str],
) -> Optional[Attendee]:
    """Fuzzy-match name+company against attendees. Returns the best candidate
    above FUZZ_THRESHOLD, or None."""
    # Quick exact match on name first (cheap)
    result = await db.execute(select(Attendee))
    candidates = list(result.scalars().all())
    best = None
    best_score = 0
    for a in candidates:
        if not a.name:
            continue
        name_score = fuzz.token_set_ratio(name.lower(), a.name.lower())
        if name_score < FUZZ_THRESHOLD:
            continue
        company_score = 100
        if company and a.company:
            company_score = fuzz.token_set_ratio(company.lower(), a.company.lower())
        # Combined score: name dominates, company is a tie-breaker / boost
        score = name_score * 0.7 + company_score * 0.3
        if score > best_score:
            best_score = score
            best = a
    return best if best_score >= FUZZ_THRESHOLD else None


async def upsert_intro(
    db: AsyncSession,
    requester_id,
    target: Optional[Attendee],
    target_name_raw: str,
    target_company_raw: Optional[str],
    source: str,
    stats: IngestStats,
):
    # Dedup on (requester, name_raw, company_raw). DB unique constraint also enforces.
    existing = await db.execute(
        select(RequestedIntro).where(
            RequestedIntro.requester_attendee_id == requester_id,
            RequestedIntro.target_name_raw == target_name_raw,
            RequestedIntro.target_company_raw == target_company_raw,
        )
    )
    if existing.scalars().first():
        stats.skipped_duplicate += 1
        return
    intro = RequestedIntro(
        requester_attendee_id=requester_id,
        target_attendee_id=target.id if target else None,
        target_name_raw=target_name_raw,
        target_company_raw=target_company_raw,
        source=source,
    )
    db.add(intro)
    stats.inserted += 1


async def run(args: argparse.Namespace) -> int:
    async with async_session_maker() as db:
        # Resolve the requester by email
        result = await db.execute(select(Attendee).where(Attendee.email == args.requester_email.lower()))
        requester = result.scalars().first()
        if not requester:
            print(f"ERROR: no attendee found for email {args.requester_email}", file=sys.stderr)
            return 2

        rows = parse_csv(
            Path(args.sheet_csv),
            name_col=args.name_col,
            company_col=args.company_col,
            notes_col=args.notes_col,
        )
        stats = IngestStats(rows_read=len(rows))

        for row in rows:
            target = await match_target(db, row["name"], row["company"])
            if target:
                stats.matched += 1
            else:
                stats.missed += 1
                stats.misses.append({"name": row["name"], "company": row["company"]})

            await upsert_intro(
                db,
                requester_id=requester.id,
                target=target,
                target_name_raw=row["name"],
                target_company_raw=row["company"],
                source=args.source,
                stats=stats,
            )

        if args.dry_run:
            await db.rollback()
            print(f"[DRY RUN] {stats.summary()}")
        else:
            await db.commit()
            print(f"[COMMITTED] {stats.summary()}")

        # Misses report
        report_path = Path(args.misses_report)
        report_path.write_text(json.dumps(stats.misses, indent=2))
        print(f"Misses report written to {report_path}")

    return 0


def main():
    p = argparse.ArgumentParser(description="Ingest priority intro requests from a CSV.")
    p.add_argument("--sheet-csv", required=True, help="Path to a CSV exported from one Sheet tab.")
    p.add_argument("--requester-email", required=True, help="Email of the requester attendee.")
    p.add_argument("--source", default="manual", help="Provenance tag stored on each intro row.")
    p.add_argument("--name-col", default="Name")
    p.add_argument("--company-col", default="Company")
    p.add_argument("--notes-col", default="Notes")
    p.add_argument("--misses-report", default="exports/intro_misses.json")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--confirm", dest="dry_run", action="store_false")
    args = p.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 7.4: Make sure rapidfuzz is in requirements**

```bash
grep -i rapidfuzz backend/requirements.txt || echo "rapidfuzz>=3.0.0" >> backend/requirements.txt
pip install -r backend/requirements.txt
```

Expected: rapidfuzz installed (or already present).

- [ ] **Step 7.5: Run the test — must pass**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_requested_intros_ingest.py -v
```

Expected: 4 passed.

- [ ] **Step 7.6: Commit**

```bash
git add backend/scripts/ingest_requested_intros.py backend/tests/test_requested_intros_ingest.py backend/requirements.txt
git commit -m "feat(ingest): script to load priority intro requests from CSV"
```

---

## Task 8: Frontend types — extend Match + add PriorityIntro

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 8.1: Extend Match type**

Find the existing `Match` interface in `frontend/src/types/index.ts` (the one with `tier?: "curated" | "deep"` around line 57). Update it:

```typescript
  tier?: "curated" | "deep" | "priority_intro";
  accepted_a_at?: string | null;
  accepted_b_at?: string | null;
  priority_intro_meta?: {
    requested_at?: string;
    target_in_db?: boolean;
    concierge_note?: string | null;
  } | null;
```

- [ ] **Step 8.2: Add the PriorityIntro type**

Anywhere in `frontend/src/types/index.ts`:

```typescript
export interface PriorityIntro {
  id: string;
  requester_attendee_id: string;
  target_attendee_id: string | null;
  target_name_raw: string;
  target_company_raw: string | null;
  source: string;
  added_at: string;
  resolved_at: string | null;
  target: Attendee | null;
  match_id: string | null;
}
```

- [ ] **Step 8.3: Confirm typecheck still passes**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: no type errors related to Match or PriorityIntro.

- [ ] **Step 8.4: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(types): extend Match with priority_intro, add PriorityIntro"
```

---

## Task 9: Frontend — render priority intro section in MyMatches

**Files:**
- Modify: `frontend/src/pages/MyMatches.tsx`
- Modify: `frontend/src/api/client.ts` (new API call)

- [ ] **Step 9.1: Add an API helper in `frontend/src/api/client.ts`**

Add to the existing exports (find a similar `getMatches` function for the pattern):

```typescript
export async function getPriorityIntros(): Promise<PriorityIntro[]> {
  const { data } = await api.get<PriorityIntro[]>("/matches/priority-intros");
  return data;
}

export async function getMagicPriorityIntros(token: string): Promise<PriorityIntro[]> {
  const { data } = await api.get<PriorityIntro[]>(`/matches/m/${token}/priority-intros`);
  return data;
}
```

Make sure `PriorityIntro` is imported from `"../types"` at the top of `client.ts`.

- [ ] **Step 9.2: Render the priority intro section in MyMatches**

In `frontend/src/pages/MyMatches.tsx`:

- Add a `useQuery(["priority-intros"], getPriorityIntros)` near the existing matches query.
- Render BEFORE the curated section (and only when the list is non-empty):

```tsx
{priorityIntros && priorityIntros.length > 0 && (
  <section className="mb-8">
    <h2 className="text-xl font-bold text-white mb-1">Your priority intros</h2>
    <p className="text-sm text-zinc-400 mb-4">
      From your concierge request. William may reach out about these.
    </p>
    <div className="space-y-4">
      {priorityIntros.map((intro) => {
        // Resolved targets: find the corresponding match row in the existing
        // matches list and render via the standard MatchCard component.
        if (intro.target_attendee_id && intro.match_id) {
          const match = matches?.find((m) => m.id === intro.match_id);
          if (match) return <MatchCard key={intro.id} match={match} />;
        }
        // Unresolved: render greyed-out card
        return (
          <div key={intro.id} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 opacity-70">
            <div className="text-sm font-medium text-zinc-300">{intro.target_name_raw}</div>
            {intro.target_company_raw && (
              <div className="text-xs text-zinc-500">{intro.target_company_raw}</div>
            )}
            <div className="mt-2 text-xs text-amber-400/80">
              Not yet attending — we'll let you know if they register.
            </div>
          </div>
        );
      })}
    </div>
  </section>
)}
```

Also filter `matches` to skip ones already rendered above (their `tier === "priority_intro"`), since those land in the priority section via `intro.match_id` lookup. Existing curated/deep rendering remains untouched.

- [ ] **Step 9.3: Smoke-test the dev server**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173/matches as an attendee with priority intros (locally seed one via `psql` or wait for the ingest script). Verify the "Your priority intros" section renders above curated and that unresolved entries show greyed-out.

Type-check:

```bash
cd frontend && npm run build
```

Expected: build succeeds, no type errors.

- [ ] **Step 9.4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/pages/MyMatches.tsx
git commit -m "feat(frontend): render priority intro section in MyMatches"
```

---

## Task 10: Frontend — render priority intro section in MagicMatches

**Files:**
- Modify: `frontend/src/pages/MagicMatches.tsx`

- [ ] **Step 10.1: Reuse the MyMatches pattern**

In `frontend/src/pages/MagicMatches.tsx`:

- Add `useQuery(["magic-priority-intros", token], () => getMagicPriorityIntros(token), { enabled: !!token })`.
- Render the same `<section>` block from Task 9 above the existing curated section.
- The MatchCard component should already work with magic-link mode (it uses the `m/:token` accept endpoint already from Phase 2 of the magic-link work).

Code pattern:

```tsx
const { data: priorityIntros } = useQuery({
  queryKey: ["magic-priority-intros", token],
  queryFn: () => getMagicPriorityIntros(token),
  enabled: !!token,
});

// Then the same JSX block from Task 9
```

- [ ] **Step 10.2: Build + smoke-test**

```bash
cd frontend && npm run build
```

Expected: build succeeds. Manually visit `/m/<token>` for an attendee with priority intros and confirm the section renders.

- [ ] **Step 10.3: Commit**

```bash
git add frontend/src/pages/MagicMatches.tsx
git commit -m "feat(frontend): render priority intro section in MagicMatches"
```

---

## Task 11: Documentation + post-merge living docs

- [ ] **Step 11.1: Append session log entry**

In `session_log.md`:

```markdown
## 2026-05-XX — Priority intro requests (Elliptic gold-tier perk)

- Added `requested_intros` table + `matches.accepted_*_at` columns (migration 9b3e2d1a8c4f)
- New `priority_intro` tier surfaces concierge-curated targets at the top of /matches with honest factual cards (no GPT fabrication)
- Per-attendee cap at 50; force-include for out-of-pool targets
- New endpoints: GET /matches/priority-intros (authed) and /matches/m/{token}/priority-intros (magic-link)
- Ingest script: `scripts/ingest_requested_intros.py --sheet-csv ... --requester-email ... --confirm`
- Tests: 4 ingest + 4 matching + 4 endpoint + 4 timestamp = 16 new
```

- [ ] **Step 11.2: Update whats_next.md**

Move `[elliptic-vip-target-list]` (if listed) to Done. Add a Now entry:

```markdown
- **[priority-intros]** Sheet `1g40iZM_utxjG_aPzynDmOwny8g_iQKv0FAHyj6RWE5I` ingest still pending sheet access (share to shaunkudzi@gmail.com OR CSV in backend/data/). Once unblocked: export each tab as CSV, run `python scripts/ingest_requested_intros.py --sheet-csv <each-tab> --requester-email <aylin|ylli|oliver email> --source elliptic_2026_05_28 --confirm`, then trigger match-refresh per requester so the new tier surfaces immediately.
```

- [ ] **Step 11.3: Update project_state.md**

Add to "What's Working":

```markdown
- **Priority intro requests (2026-05-XX, LIVE)** — concierge-curated per-attendee target lists surface as a new `priority_intro` match tier above curated, with honest factual cards and `matches.accepted_*_at` timestamps for ROI audit. Force-include cap 50. Gold-tier sponsor perk; first client Elliptic (5 attendees, 3 with target lists).
```

- [ ] **Step 11.4: Commit docs**

```bash
git add session_log.md whats_next.md project_state.md
git commit -m "docs: priority intro requests live"
```

---

## Task 12: Deploy + ingest

- [ ] **Step 12.1: Apply migration to prod Supabase**

```bash
cd backend && source .venv/bin/activate
# Ensure DATABASE_URL points to prod (:6543 pooler)
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade 24a02695202e -> 9b3e2d1a8c4f`

- [ ] **Step 12.2: Push to main → Railway auto-deploys**

```bash
git push origin main
```

Wait ~5 min for Railway to finish deploying. Smoke check:

```bash
curl -i https://meet.proofoftalk.io/api/v1/matches/priority-intros
```

Expected: 401 (auth required) — confirms the route is live.

- [ ] **Step 12.3: Wait for sheet access**

User unblocks the Elliptic sheet (share to shaunkudzi@gmail.com OR drop CSV in `backend/data/`).

- [ ] **Step 12.4: Ingest each tab**

For each tab (Aylin, Ylli, Oliver):

```bash
cd backend && source .venv/bin/activate
python scripts/ingest_requested_intros.py \
    --sheet-csv backend/data/elliptic_aylin.csv \
    --requester-email <aylin's email> \
    --source elliptic_2026_05_28 \
    --dry-run

# Review --dry-run output. Confirm match/miss counts. Then re-run:

python scripts/ingest_requested_intros.py \
    --sheet-csv backend/data/elliptic_aylin.csv \
    --requester-email <aylin's email> \
    --source elliptic_2026_05_28 \
    --confirm
```

Repeat for ylli + oliver tabs.

- [ ] **Step 12.5: Trigger match refresh per requester**

```bash
python -c "
import asyncio
from app.services.profile_pipeline import refresh_profile_matches
asyncio.run(refresh_profile_matches('<aylin-attendee-id>'))
"
```

Repeat per requester.

- [ ] **Step 12.6: Smoke-test live**

Open `https://meet.proofoftalk.io/m/<aylin-magic-token>` and confirm the "Your priority intros" section renders.

- [ ] **Step 12.7: Tell William**

Notify operator (Karl or William) that the data is live, share the magic links for the three Elliptic attendees, and confirm William can start soft intros.

---

## Self-review notes

- **Test approach:** the test code shown is **behavioural** — when implementing each test task, translate the asserted behaviour into the mock-DB pattern (see `test_adoption_endpoint.py`). Each test stubs `db.execute.side_effect = [...]` with the expected query results in order. Resist the urge to introduce real-DB fixtures.
- All sheet column names default to `Name | Company | Notes` and are overridable via CLI flags. Real column mapping is confirmed against the actual sheet during Task 12.4 — adjust the flags if the headers differ.
- The `_apply_priority_intros` helper is called once per `generate_matches_for_attendee` invocation. The 03:30 UTC `_daily_match_refresh` cron only fires for net-new attendees, so existing priority-intro requesters won't auto-refresh — Task 12.5 explicitly triggers a refresh per requester to surface the new tier.
- `match_target` does a full table scan (loads all attendees, then fuzzy-matches in Python). At ~1300 attendees that's fine for an operator-triggered batch. If the sheet ever grows to thousands of targets, switch to a database trigram index on `attendees.name`.
- The `priority_intro_meta` field on `MatchResponse` is currently unused — the frontend reads from `getPriorityIntros()` directly. Field kept for future-proofing per the spec; remove if it stays unused after a month.
- The `Match` symbol is already imported in `matching.py` and `matches.py` — no new import needed in Task 5.4 / Task 6.3 beyond the new `RequestedIntro` / `PriorityIntroResponse` additions.
