# Speaker Consent Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude 17 flagged high-profile speakers from matching (both directions) until they consent, controlled by a `matching_consent` DB flag, and scrub the 8 already-live matches.

**Architecture:** A new `attendees.matching_consent` string column (default `not_required`). A duck-typed `is_match_gated()` predicate gates `pending`/`declined` rows at the same two matching boundaries `staff_filter` already uses. A one-time seed reads the orange `#f9cb9c` cells from the `2026 - Confirmed Speakers` sheet; a CLI flips consent as confirmations arrive; a scrub removes existing gated matches.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Supabase REST (httpx), Google Sheets API (google-auth), pytest.

---

## File Structure

- Create: `backend/app/services/consent_filter.py` — `is_match_gated()` predicate (one responsibility: decide if an attendee is gated)
- Create: `backend/tests/test_consent_filter.py` — unit tests for the predicate
- Modify: `backend/app/models/attendee.py` — add `matching_consent` column
- Create: `backend/alembic/versions/<rev>_add_matching_consent.py` — migration
- Modify: `backend/app/services/matching.py` — gate at `_is_candidate_eligible` (candidate side) + `generate_matches_for_attendee` (subject side)
- Create: `backend/scripts/seed_speaker_consent.py` — seed `pending` from the sheet + `--scrub-matches`
- Create: `backend/scripts/set_speaker_consent.py` — grant/list CLI

---

## Task 1: `is_match_gated` predicate (TDD)

**Files:**
- Create: `backend/app/services/consent_filter.py`
- Test: `backend/tests/test_consent_filter.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_consent_filter.py
from types import SimpleNamespace
from app.services.consent_filter import is_match_gated


def test_pending_is_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="pending")) is True

def test_declined_is_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="declined")) is True

def test_granted_not_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="granted")) is False

def test_not_required_not_gated():
    assert is_match_gated(SimpleNamespace(matching_consent="not_required")) is False

def test_missing_attr_not_gated():
    assert is_match_gated(SimpleNamespace()) is False

def test_none_value_not_gated():
    assert is_match_gated(SimpleNamespace(matching_consent=None)) is False

def test_dict_form_gated():
    assert is_match_gated({"matching_consent": "pending"}) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_consent_filter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.consent_filter'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/consent_filter.py
"""Consent gate for matching.

High-profile speakers must not appear in the matchmaker until they consent.
Their attendee row carries matching_consent in {pending, declined} until then.
Mirrors the duck-typed accessor style of staff_filter.is_internal_staff so it
works with both ORM Attendee instances and plain dicts.
"""
from typing import Any

GATED_STATES = {"pending", "declined"}


def is_match_gated(attendee: Any) -> bool:
    """True if this attendee is withheld from matching pending/declining consent."""
    if isinstance(attendee, dict):
        val = attendee.get("matching_consent")
    else:
        val = getattr(attendee, "matching_consent", None)
    return (val or "not_required") in GATED_STATES
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_consent_filter.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consent_filter.py backend/tests/test_consent_filter.py
git commit -m "feat(consent): is_match_gated predicate + tests"
```

---

## Task 2: Add `matching_consent` column to the model + migration

**Files:**
- Modify: `backend/app/models/attendee.py` (add column near the other String columns, e.g. after `email`)
- Create: `backend/alembic/versions/<rev>_add_matching_consent.py`

- [ ] **Step 1: Add the column to the model**

In `backend/app/models/attendee.py`, add (matching the existing `Mapped[...] = mapped_column(...)` style):

```python
    # Speaker consent gate. "not_required" (default, matchable) / "pending"
    # (flagged high-profile, awaiting consent) / "granted" (consented) /
    # "declined" (said no). pending+declined are excluded from matching.
    matching_consent: Mapped[str] = mapped_column(
        String(32), server_default="not_required", nullable=False
    )
```

(Confirm `String` is already imported at the top of the file; it is used by `email`.)

- [ ] **Step 2: Create the Alembic migration**

Run: `cd backend && source .venv/bin/activate && alembic revision -m "add matching_consent to attendees"`
Then replace the generated `upgrade()`/`downgrade()` bodies with:

```python
import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "attendees",
        sa.Column(
            "matching_consent",
            sa.String(length=32),
            server_default="not_required",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("attendees", "matching_consent")
```

- [ ] **Step 3: Apply the migration**

Run: `cd backend && source .venv/bin/activate && alembic upgrade head`
Expected: completes without error; `alembic current` shows the new revision.

- [ ] **Step 4: Verify the column exists + defaults correctly**

Run:
```bash
cd backend && source .venv/bin/activate && python -c "
import os, httpx
from dotenv import load_dotenv
load_dotenv('.env')
U=os.getenv('SUPABASE_URL'); K=os.getenv('SUPABASE_SERVICE_ROLE_KEY')
h={'apikey':K,'Authorization':f'Bearer {K}'}
r=httpx.get(f'{U}/rest/v1/attendees', headers=h|{'Prefer':'count=exact','Range':'0-0','Range-Unit':'items'}, params={'select':'id','matching_consent':'eq.not_required'}, timeout=30)
print('rows defaulted to not_required:', r.headers.get('content-range'))
"
```
Expected: the content-range total equals the full attendee count (all existing rows defaulted).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/attendee.py backend/alembic/versions/
git commit -m "feat(consent): add attendees.matching_consent column + migration"
```

---

## Task 3: Gate matching at both boundaries

**Files:**
- Modify: `backend/app/services/matching.py` (`_is_candidate_eligible` ~line 226-233; `generate_matches_for_attendee` ~line 608)

- [ ] **Step 1: Gate the candidate side**

In `_is_candidate_eligible`, immediately after the existing staff-filter block:

```python
        from app.services.staff_filter import is_internal_staff
        if is_internal_staff(candidate):
            return False

        # Consent gate: high-profile speakers withheld until they consent.
        from app.services.consent_filter import is_match_gated
        if is_match_gated(candidate):
            return False
```

- [ ] **Step 2: Gate the subject side**

At the very start of `generate_matches_for_attendee` (after the signature/docstring, before any candidate retrieval), add:

```python
        from app.services.consent_filter import is_match_gated
        if is_match_gated(attendee):
            return []  # gated — generate no matches for this attendee
```

(Confirm the function's normal return type is a list of match objects; returning `[]` matches it.)

- [ ] **Step 3: Write an integration test**

```python
# backend/tests/test_consent_filter.py  (append)
from app.services.matching import MatchingEngine

def test_candidate_eligibility_excludes_gated():
    eng = MatchingEngine.__new__(MatchingEngine)  # no DB needed for this method
    attendee = SimpleNamespace(matching_consent="not_required", not_looking_for=[],
                               preferred_geographies=[], ticket_type="delegate", deal_stage=None)
    gated = SimpleNamespace(matching_consent="pending", not_looking_for=[],
                            preferred_geographies=[], ticket_type="speaker", deal_stage=None)
    assert eng._is_candidate_eligible(attendee, gated) is False
```

If `_is_candidate_eligible` calls helpers that need more attributes, give the
`SimpleNamespace` stubs those attributes (read the method first and mirror what
it accesses). The assertion that matters: a `pending` candidate is ineligible.

- [ ] **Step 4: Run tests**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_consent_filter.py -v`
Expected: PASS (all, including the new integration test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/matching.py backend/tests/test_consent_filter.py
git commit -m "feat(consent): gate pending/declined speakers at both matching boundaries"
```

---

## Task 4: Seed script — flag the 17 + scrub live matches

**Files:**
- Create: `backend/scripts/seed_speaker_consent.py`

- [ ] **Step 1: Write the seed script**

```python
# backend/scripts/seed_speaker_consent.py
"""Seed matching_consent='pending' for high-profile speakers flagged orange
(#f9cb9c) on column B of the '2026 - Confirmed Speakers' sheet tab, and
optionally scrub existing matches that involve a now-gated speaker.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/seed_speaker_consent.py --dry-run      # report only
    python scripts/seed_speaker_consent.py                # set pending
    python scripts/seed_speaker_consent.py --scrub-matches  # set pending + delete gated matches
"""
import argparse, json, os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SHEET_ID = "1DJJ5vQ-t4qJli1nI5oOwy94cAY98svTQ90vTMqXceNY"
CONFIRMED_TAB = "2026 - Confirmed Speakers"
ORANGE_HEX = "#f9cb9c"
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def _hexc(col) -> str:
    if not col:
        return "default"
    return "#%02x%02x%02x" % (
        round(col.get("red", 0) * 255), round(col.get("green", 0) * 255), round(col.get("blue", 0) * 255),
    )


def fetch_orange_names() -> list[str]:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    creds.refresh(Request())
    r = httpx.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}",
        params=[("ranges", f"'{CONFIRMED_TAB}'!B4:D280"),
                ("fields", "sheets(data(rowData(values(formattedValue,effectiveFormat(backgroundColor)))))")],
        headers={"Authorization": f"Bearer {creds.token}"}, timeout=40,
    )
    r.raise_for_status()
    rows = r.json()["sheets"][0]["data"][0].get("rowData", [])
    names = []
    for row in rows:
        vals = row.get("values", [])
        if not vals:
            continue
        fn = vals[0].get("formattedValue", "")
        if not fn:
            continue
        if _hexc(vals[0].get("effectiveFormat", {}).get("backgroundColor")) == ORANGE_HEX:
            ln = vals[1].get("formattedValue", "") if len(vals) > 1 else ""
            names.append(f"{fn} {ln}".strip())
    return names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scrub-matches", action="store_true")
    args = ap.parse_args()

    orange = fetch_orange_names()
    print(f"Orange (#f9cb9c) speakers in sheet: {len(orange)}")

    att = httpx.get(f"{SUPA_URL}/rest/v1/attendees", headers=H,
                    params={"select": "id,name,matching_consent"}, timeout=60).json()
    by_name = {_norm(a["name"]): a for a in att}

    to_set, missing = [], []
    for n in orange:
        a = by_name.get(_norm(n))
        if a:
            to_set.append(a)
        else:
            missing.append(n)

    print(f"  matched in DB: {len(to_set)}   not in DB: {len(missing)} {missing}")
    if args.dry_run:
        for a in to_set:
            print(f"    would set pending: {a['name']} (now {a['matching_consent']})")
        return

    # Set pending, but never downgrade an already-granted row.
    set_ids = []
    for a in to_set:
        if a["matching_consent"] == "granted":
            print(f"    skip (already granted): {a['name']}")
            continue
        httpx.patch(f"{SUPA_URL}/rest/v1/attendees", headers=H | {"Prefer": "return=minimal"},
                    params={"id": f"eq.{a['id']}"}, json={"matching_consent": "pending"}, timeout=30)
        set_ids.append(a["id"])
    print(f"  set pending: {len(set_ids)}")

    if args.scrub_matches and set_ids:
        ids_filter = f"in.({','.join(set_ids)})"
        total = 0
        for col in ("attendee_a_id", "attendee_b_id"):
            r = httpx.delete(f"{SUPA_URL}/rest/v1/matches",
                             headers=H | {"Prefer": "return=representation"},
                             params={col: ids_filter}, timeout=60)
            total += len(r.json()) if r.status_code == 200 else 0
        print(f"  scrubbed {total} matches involving gated speakers")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run to verify the match (no writes)**

Run: `cd backend && source .venv/bin/activate && python scripts/seed_speaker_consent.py --dry-run`
Expected: "Orange ... speakers in sheet: 17", "matched in DB: 16   not in DB: 1 ['Tom Lee']", and 16 "would set pending" lines.

- [ ] **Step 3: Commit (script only; the live run happens in Task 6)**

```bash
git add backend/scripts/seed_speaker_consent.py
git commit -m "feat(consent): seed script for orange-flagged speakers + match scrub"
```

---

## Task 5: Grant CLI

**Files:**
- Create: `backend/scripts/set_speaker_consent.py`

- [ ] **Step 1: Write the CLI**

```python
# backend/scripts/set_speaker_consent.py
"""Flip a speaker's matching_consent as confirmations arrive from Sneha.

Usage:
    python scripts/set_speaker_consent.py --list
    python scripts/set_speaker_consent.py --name "Stani Kulechov" --status granted
"""
import argparse, os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}
VALID = {"not_required", "pending", "granted", "declined"}


def _norm(s): return " ".join((s or "").lower().split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--name")
    ap.add_argument("--status", choices=sorted(VALID))
    args = ap.parse_args()

    if args.list:
        rows = httpx.get(f"{SUPA_URL}/rest/v1/attendees", headers=H,
                         params={"select": "name,company,matching_consent",
                                 "matching_consent": "neq.not_required",
                                 "order": "matching_consent,name"}, timeout=60).json()
        print(f"{len(rows)} gated/consented speakers:")
        for r in rows:
            print(f"  [{r['matching_consent']:<9}] {r['name']} — {r.get('company','')}")
        return

    if not args.name or not args.status:
        ap.error("provide --name and --status, or --list")

    rows = httpx.get(f"{SUPA_URL}/rest/v1/attendees", headers=H,
                     params={"select": "id,name,matching_consent"}, timeout=60).json()
    matches = [a for a in rows if _norm(a["name"]) == _norm(args.name)]
    if not matches:
        print(f"No attendee named {args.name!r}")
        return
    if len(matches) > 1:
        print(f"Ambiguous — {len(matches)} rows named {args.name!r}; resolve by hand.")
        return
    a = matches[0]
    httpx.patch(f"{SUPA_URL}/rest/v1/attendees", headers=H | {"Prefer": "return=minimal"},
                params={"id": f"eq.{a['id']}"}, json={"matching_consent": args.status}, timeout=30)
    print(f"{a['name']}: {a['matching_consent']} -> {args.status}")
    print("Run a match refresh (or wait for the 02:45 UTC cron) to (de)apply.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify --list runs (read-only)**

Run: `cd backend && source .venv/bin/activate && python scripts/set_speaker_consent.py --list`
Expected: prints current gated/consented speakers (likely empty until Task 6 runs the seed).

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/set_speaker_consent.py
git commit -m "feat(consent): grant/list CLI for speaker consent"
```

---

## Task 6: Run Phase 0 (seed + scrub), deploy, verify

**Files:** none (operational)

- [ ] **Step 1: Run the seed + scrub against production data**

Run: `cd backend && source .venv/bin/activate && python scripts/seed_speaker_consent.py --scrub-matches`
Expected: "set pending: 16", "scrubbed N matches involving gated speakers" (N ≥ 8).

- [ ] **Step 2: Verify the 8 live ones are gated + scrubbed**

Run: `cd backend && source .venv/bin/activate && python scripts/set_speaker_consent.py --list`
Expected: 16 rows all `[pending]` (Franklin Templeton, Aave, Robinhood, etc.).

Then confirm none remain in matches:
```bash
cd backend && source .venv/bin/activate && python -c "
import os, httpx
from dotenv import load_dotenv
load_dotenv('.env')
U=os.getenv('SUPABASE_URL'); K=os.getenv('SUPABASE_SERVICE_ROLE_KEY')
h={'apikey':K,'Authorization':f'Bearer {K}'}
ids=[a['id'] for a in httpx.get(f'{U}/rest/v1/attendees',headers=h,params={'select':'id','matching_consent':'eq.pending'},timeout=60).json()]
f=f'in.({chr(44).join(ids)})'
n=0
for c in ('attendee_a_id','attendee_b_id'):
    n+=len(httpx.get(f'{U}/rest/v1/matches',headers=h,params={'select':'id',c:f},timeout=60).json())
print('gated speakers still in matches:', n)
"
```
Expected: `gated speakers still in matches: 0`

- [ ] **Step 3: Run the full test suite**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_consent_filter.py -v`
Expected: all PASS.

- [ ] **Step 4: Push (deploys the code-level filter via Railway)**

```bash
git push origin main
```
Note: Railway may be slow if the build incident persists; the Phase 0 data
action in Step 1 already closed the live exposure regardless of deploy timing.

- [ ] **Step 5: Update living docs**

Append a `session_log.md` entry (consent gate shipped: column + filter + seed/grant scripts, 16 set pending, N matches scrubbed, Tom Lee not-in-DB pending reconciliation). Mark the consent-gate item done in `whats_next.md` and note the speaker-data reconciliation follow-up. Update `project_state.md`. Commit.

```bash
git add session_log.md whats_next.md project_state.md
git commit -m "docs: speaker consent gate shipped"
git push origin main
```

---

## Self-Review

- **Spec coverage:** data model (Task 2) ✓, both exclusion points (Task 3) ✓, seed from orange (Task 4) ✓, grant CLI (Task 5) ✓, Phase 0 seed+scrub (Task 6) ✓, tests (Tasks 1, 3) ✓. All spec sections covered.
- **Placeholders:** none — every step has real code/commands.
- **Type consistency:** `is_match_gated` defined in Task 1, imported identically in Task 3; `matching_consent` string values consistent across model, scripts, predicate (`not_required`/`pending`/`granted`/`declined`).
- **Note for executor:** read `_is_candidate_eligible` before Task 3 Step 3 and give the test stubs whatever attributes the method touches; the load-bearing assertion is that a `pending` candidate is ineligible.
