# User-Editable AI Write-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let attendees edit their own AI write-up (`ai_summary`) on the Profile page, with the edit pinned so the AI never auto-overwrites it, plus a Regenerate button.

**Architecture:** Add a boolean pin flag to `attendees`. `process_attendee` skips summary regeneration when pinned (single guard covers all refresh paths). `PUT /auth/profile` accepts `ai_summary` (pins on non-empty, un-pins on empty). New `POST /auth/profile/regenerate-summary` returns a fresh AI draft without saving. Profile page gets an editable textarea + Regenerate button.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, pytest; React + TypeScript (Vite).

**Spec:** `docs/superpowers/specs/2026-05-25-user-editable-ai-writeup-design.md`

---

### Task 1: Add `ai_summary_pinned` + `ai_summary_edited_at` (model + migration)

**Files:**
- Modify: `backend/app/models/attendee.py` (Attendee class, near the existing `ai_summary` field)
- Create: `backend/alembic/versions/<rev>_add_ai_summary_pin.py`

- [ ] **Step 1: Add columns to the Attendee model**

In `attendee.py`, in the `Attendee` class immediately after the existing `ai_summary` column, add:

```python
    # User-editable write-up: when pinned, the AI never auto-regenerates ai_summary
    ai_summary_pinned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    ai_summary_edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

(`Boolean`, `DateTime`, `Mapped`, `mapped_column`, `datetime` are already imported in this file.)

- [ ] **Step 2: Create the migration**

Run: `cd backend && source .venv/bin/activate && alembic revision -m "add ai_summary pin"`
Set `down_revision = "a6dda3ac7276"`. Body:

```python
def upgrade() -> None:
    op.add_column("attendees", sa.Column("ai_summary_pinned", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("attendees", sa.Column("ai_summary_edited_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("attendees", "ai_summary_edited_at")
    op.drop_column("attendees", "ai_summary_pinned")
```

- [ ] **Step 3: Apply migration (prod DB per playbook — DATABASE_URL is prod)**

Run: `alembic upgrade head`
Expected: `Running upgrade a6dda3ac7276 -> <rev>`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/attendee.py backend/alembic/versions/
git commit -m "feat: add ai_summary_pinned + edited_at columns"
```

---

### Task 2: Pin guard in `process_attendee`

**Files:**
- Modify: `backend/app/services/matching.py:172`
- Test: `backend/tests/test_ai_summary_pin.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio, uuid
from unittest.mock import AsyncMock, patch
import pytest
from app.models.attendee import Attendee
from app.services.matching import MatchingEngine

def _attendee(**kw):
    a = Attendee(id=uuid.uuid4(), name="T", email="t@x.co", company="C")
    a.ai_summary = "ORIGINAL USER TEXT"
    for k, v in kw.items():
        setattr(a, k, v)
    return a

@pytest.mark.asyncio
async def test_process_attendee_preserves_pinned_summary():
    a = _attendee(ai_summary_pinned=True)
    eng = MatchingEngine(db=AsyncMock())
    with patch("app.services.matching.generate_ai_summary", new=AsyncMock(return_value="AI REWRITE")) as gen, \
         patch("app.services.matching.classify_intents", new=AsyncMock(return_value=["knowledge_exchange"])), \
         patch("app.services.matching.infer_customer_profile", new=AsyncMock(return_value={})), \
         patch("app.services.matching.embed_attendee", new=AsyncMock(return_value=[0.0])):
        await eng.process_attendee(a)
    gen.assert_not_called()
    assert a.ai_summary == "ORIGINAL USER TEXT"

@pytest.mark.asyncio
async def test_process_attendee_regenerates_when_not_pinned():
    a = _attendee(ai_summary_pinned=False)
    eng = MatchingEngine(db=AsyncMock())
    with patch("app.services.matching.generate_ai_summary", new=AsyncMock(return_value="AI REWRITE")), \
         patch("app.services.matching.classify_intents", new=AsyncMock(return_value=["knowledge_exchange"])), \
         patch("app.services.matching.infer_customer_profile", new=AsyncMock(return_value={})), \
         patch("app.services.matching.embed_attendee", new=AsyncMock(return_value=[0.0])):
        await eng.process_attendee(a)
    assert a.ai_summary == "AI REWRITE"
```

- [ ] **Step 2: Run, verify it fails**

Run: `pytest tests/test_ai_summary_pin.py -v`
Expected: FAIL (currently always regenerates → first test fails).

- [ ] **Step 3: Add the guard**

In `matching.py` `process_attendee`, replace:

```python
        attendee.ai_summary = await generate_ai_summary(attendee)
```

with:

```python
        # Respect a user-pinned write-up: never auto-overwrite it.
        if not getattr(attendee, "ai_summary_pinned", False):
            attendee.ai_summary = await generate_ai_summary(attendee)
```

- [ ] **Step 4: Run, verify pass**

Run: `pytest tests/test_ai_summary_pin.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/matching.py backend/tests/test_ai_summary_pin.py
git commit -m "feat: skip ai_summary regeneration when pinned"
```

---

### Task 3: `PUT /auth/profile` accepts `ai_summary`

**Files:**
- Modify: `backend/app/api/routes/auth.py` (`update_profile`, the `allowed` set + a new handling block)
- Test: `backend/tests/test_profile_ai_summary_edit.py`

- [ ] **Step 1: Write the failing test** (uses the app's async test client + db; mirror `tests/test_login_last_login.py` for fixtures)

```python
import pytest
# Reuse existing client/auth fixtures from conftest.py; this test asserts the
# behaviour contract on the attendee row after PUT /auth/profile.
# (If conftest lacks an authed-client fixture, add one mirroring test_login_last_login.py.)

@pytest.mark.asyncio
async def test_edit_ai_summary_pins(authed_client, db_attendee):
    r = await authed_client.put("/api/v1/auth/profile", json={"ai_summary": "My own bio."})
    assert r.status_code == 200
    await db_attendee.refresh()
    assert db_attendee.ai_summary == "My own bio."
    assert db_attendee.ai_summary_pinned is True
    assert db_attendee.ai_summary_edited_at is not None

@pytest.mark.asyncio
async def test_empty_ai_summary_unpins(authed_client, db_attendee):
    db_attendee.ai_summary_pinned = True
    r = await authed_client.put("/api/v1/auth/profile", json={"ai_summary": "   "})
    assert r.status_code == 200
    await db_attendee.refresh()
    assert db_attendee.ai_summary_pinned is False

@pytest.mark.asyncio
async def test_ai_summary_too_long_rejected(authed_client):
    r = await authed_client.put("/api/v1/auth/profile", json={"ai_summary": "x" * 2001})
    assert r.status_code == 400
```

- [ ] **Step 2: Run, verify it fails**

Run: `pytest tests/test_profile_ai_summary_edit.py -v`
Expected: FAIL (ai_summary not in allowed; no pin logic).

- [ ] **Step 3: Implement in `update_profile`**

Add `"ai_summary"` is intentionally NOT added to the generic `allowed` loop (it needs special pin handling). Instead, before the `for field, value in data.items()` loop, add:

```python
    from datetime import datetime
    if "ai_summary" in data:
        raw = (data.get("ai_summary") or "").strip()
        if len(raw) > 2000:
            raise HTTPException(status_code=400, detail="Write-up must be 2000 characters or fewer.")
        if raw:
            attendee.ai_summary = raw
            attendee.ai_summary_pinned = True
            attendee.ai_summary_edited_at = datetime.utcnow()
        else:
            # Empty = "reset to AI": un-pin and let the refresh below regenerate.
            attendee.ai_summary_pinned = False
        data = {k: v for k, v in data.items() if k != "ai_summary"}
```

(The existing code then continues with the generic `allowed` loop, sets `attendee.embedding = None`, commits, and fires `refresh_profile_matches` — which now preserves the pinned summary and rebuilds the embedding from it.)

- [ ] **Step 4: Run, verify pass**

Run: `pytest tests/test_profile_ai_summary_edit.py -v`
Expected: PASS (3).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_profile_ai_summary_edit.py
git commit -m "feat: allow editing ai_summary via PUT /auth/profile (pin/unpin)"
```

---

### Task 4: `POST /auth/profile/regenerate-summary`

**Files:**
- Modify: `backend/app/api/routes/auth.py` (new route)
- Test: `backend/tests/test_regenerate_summary.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_regenerate_returns_draft_without_saving(authed_client, db_attendee):
    db_attendee.ai_summary = "OLD"
    db_attendee.ai_summary_pinned = True
    with patch("app.api.routes.auth.generate_ai_summary", new=AsyncMock(return_value="FRESH DRAFT")):
        r = await authed_client.post("/api/v1/auth/profile/regenerate-summary")
    assert r.status_code == 200
    assert r.json()["ai_summary"] == "FRESH DRAFT"
    await db_attendee.refresh()
    assert db_attendee.ai_summary == "OLD"          # not saved
    assert db_attendee.ai_summary_pinned is True     # pin unchanged
```

- [ ] **Step 2: Run, verify it fails**

Run: `pytest tests/test_regenerate_summary.py -v`
Expected: FAIL (404 / route missing).

- [ ] **Step 3: Implement the route** (add near `update_profile`; add `from app.services.embeddings import generate_ai_summary` to the imports at top of `auth.py`)

```python
@router.post("/profile/regenerate-summary")
@limiter.limit("10/minute")
async def regenerate_summary(
    request: Request,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return a fresh AI-drafted write-up from the current profile. Does NOT
    save and does NOT change the pin state — the client fills the textarea with
    this draft; saving it (PUT /auth/profile) is what pins it."""
    if not user.attendee_id:
        raise HTTPException(status_code=404, detail="No attendee profile linked")
    attendee = await db.get(Attendee, user.attendee_id)
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee profile not found")
    draft = await generate_ai_summary(attendee)
    return {"ai_summary": draft}
```

- [ ] **Step 4: Run, verify pass**

Run: `pytest tests/test_regenerate_summary.py -v`
Expected: PASS.

- [ ] **Step 5: Run full backend suite + commit**

```bash
pytest -q
git add backend/app/api/routes/auth.py backend/tests/test_regenerate_summary.py
git commit -m "feat: add POST /auth/profile/regenerate-summary (draft only)"
```

---

### Task 5: Frontend — editable write-up + Regenerate button

**Files:**
- Modify: `frontend/src/api/client.ts` (add `regenerateSummary`)  *(file is the one containing `updateProfile` ~line 446)*
- Modify: `frontend/src/pages/Profile.tsx`

- [ ] **Step 1: Add API method** (after `updateProfile`)

```ts
export async function regenerateSummary(): Promise<{ ai_summary: string }> {
  const { data } = await api.post("/auth/profile/regenerate-summary");
  return data;
}
```

- [ ] **Step 2: Wire form state** — add `ai_summary: ""` to the `useState` form object and to the `setForm({...})` in the load effect: `ai_summary: a.ai_summary ?? ""`. Import `regenerateSummary` and add `RefreshCw` to the lucide import.

- [ ] **Step 3: Replace the read-only AI Summary block** (`Profile.tsx` ~309–312) with an editable section:

```tsx
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Your write-up</h2>
            <button type="button" onClick={handleRegenerate} disabled={regenerating}
              className="flex items-center gap-1 text-xs text-white/60 hover:text-white">
              <RefreshCw className={`w-3 h-3 ${regenerating ? "animate-spin" : ""}`} />
              {regenerating ? "Drafting…" : "Regenerate with AI"}
            </button>
          </div>
          <textarea value={form.ai_summary} onChange={set("ai_summary")} rows={5} maxLength={2000}
            placeholder="How you're introduced to your matches…"
            className="w-full bg-white/5 rounded-lg p-3 text-sm" />
          <div className="flex justify-between text-xs text-white/40">
            <span>This is how you're introduced to your matches — edit it anytime. Your version is kept; the AI won't overwrite it.</span>
            <span>{form.ai_summary.length}/2000</span>
          </div>
        </div>
```

- [ ] **Step 4: Add the regenerate handler** (near `handleSubmit`):

```tsx
  const [regenerating, setRegenerating] = useState(false);
  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const { ai_summary } = await regenerateSummary();
      setForm((f) => ({ ...f, ai_summary }));
    } catch {
      setError("Could not regenerate the write-up.");
    } finally {
      setRegenerating(false);
    }
  };
```

(`form` already flows into `updateProfile(form)` in `handleSubmit`, so `ai_summary` is saved with the existing Save button.)

- [ ] **Step 5: Build + commit**

```bash
cd frontend && npm run build
git add frontend/src/api/client.ts frontend/src/pages/Profile.tsx
git commit -m "feat: editable AI write-up + regenerate button on Profile page"
```

---

### Task 6: Smoke test (Playwright MCP) + pin Pouneh

- [ ] **Step 1:** Run backend (`uvicorn app.main:app --reload --port 8000`) + frontend (`npm run dev`), OR verify against prod after deploy.
- [ ] **Step 2:** Playwright MCP: log in as a demo persona (`marcus@demo.proofoftalk.io` / `ProofDemo2026!`), go to `/profile`, edit the write-up, Save, reload → edited text persists. Click Regenerate → textarea fills with a new draft. Edit goals + Save → write-up unchanged.
- [ ] **Step 3:** Follow-up — set Pouneh's pin: `UPDATE attendees SET ai_summary_pinned=true, ai_summary_edited_at=now() WHERE id='3bf5d2aa-f82f-4f37-8f41-36fdabbad20b';`
- [ ] **Step 4:** Update `session_log.md`, `whats_next.md`, `project_state.md`; commit.
