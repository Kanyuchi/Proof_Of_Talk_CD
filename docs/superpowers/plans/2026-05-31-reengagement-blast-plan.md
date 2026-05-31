# Re-engagement blast - implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a one-shot operator-driven email blast to the 1,042 unregistered ticket-holders today (2026-05-31) with personalised subject + match-count value prop, with Resend open/click tracking enabled so we can measure outcome.

**Spec:** [docs/superpowers/specs/2026-05-31-reengagement-blast-design.md](../specs/2026-05-31-reengagement-blast-design.md)

**Architecture:** New `send_reengagement_email()` function in `app/services/email.py` reuses the existing `_render_email()` shell and the T-1 reminder's match-card markup. Tracking is enabled by extending `_send_email()` with an optional `tracking_options` parameter so existing transactional sends stay un-tracked. A new operator script `scripts/send_reengagement_blast.py` (mirror of `send_welcome_batch.py`) batches the cohort, computes per-recipient match context (top 2 matches + incoming-interest count) in a single query, and writes a separate ledger.

**Tech Stack:** Python 3.11+, SQLAlchemy async, httpx + Resend API, pytest, plain SQL via SQLAlchemy `text()`.

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `backend/app/services/email.py` | Add `tracking_options` to `_send_email`, add `send_reengagement_email()` | Modify |
| `backend/app/services/reengagement_blast.py` | Cohort query + per-recipient context + subject picker (importable from script + tests) | Create |
| `backend/scripts/send_reengagement_blast.py` | Operator CLI: --preview / --confirm / --limit / --only / --status | Create |
| `backend/tests/test_send_reengagement_email.py` | Unit tests for email shape + tracking flag | Create |
| `backend/tests/test_reengagement_blast_cohort.py` | Unit tests for cohort SQL + subject picker | Create |
| `backend/exports/reengagement_sent.log` | Runtime ledger (gitignored) | Created at runtime |

---

## Pre-flight

- [ ] **Confirm branch.** Check `git status` and `git branch --show-current`. If on a parallel-session branch (e.g. `fix/kiril-amara-...`), branch off `main` for clean isolation: `git fetch origin && git checkout -b feat/reengagement-blast origin/main` then cherry-pick spec commit `26659c2`. If user confirms staying on current branch is fine, skip.

- [ ] **Verify Resend tracking payload field name.** The Resend Send Email API doc lives at https://resend.com/docs/api-reference/emails/send-email. As of 2026-05, the field is `tracking_options` with `{"open_tracking": true, "click_tracking": true}` shape. If the doc has changed, adjust Task 1 accordingly.

- [ ] **Confirm prod DB is reachable.** `cd backend && source .venv/bin/activate && python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.environ['DATABASE_URL'].split('@')[1][:50])"` should print `db.mkcememoueziibbpqhfk.supabase.co:6543/...`. The script targets prod (same pattern as `send_welcome_batch.py`).

---

## Task 1: Extend `_send_email` to accept `tracking_options`

**Why first:** every subsequent send-side test depends on tracking being plumbed through.

**Files:**
- Modify: `backend/app/services/email.py:34-122` (signature + payload)
- Test: `backend/tests/test_send_reengagement_email.py` (new)

- [ ] **Step 1: Write failing test that tracking_options reaches the Resend payload**

Create `backend/tests/test_send_reengagement_email.py`:

```python
"""Tests for re-engagement email send + tracking plumbing."""
from unittest.mock import patch, MagicMock

from app.services import email as email_svc


def test_send_email_passes_tracking_options_when_provided():
    """tracking_options dict must end up in the Resend payload verbatim."""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        m = MagicMock()
        m.status_code = 200
        return m

    with patch.object(email_svc.httpx, "post", side_effect=fake_post):
        ok = email_svc._send_email(
            to_email="test@proofoftalk.io",
            subject="hi",
            html="<p>hi</p>",
            force=True,
            tracking_options={"open_tracking": True, "click_tracking": True},
        )

    assert ok is True
    assert captured["payload"]["tracking_options"] == {
        "open_tracking": True,
        "click_tracking": True,
    }


def test_send_email_omits_tracking_options_when_not_provided():
    """No tracking_options key in payload when None - preserves current behaviour."""
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        m = MagicMock()
        m.status_code = 200
        return m

    with patch.object(email_svc.httpx, "post", side_effect=fake_post):
        email_svc._send_email(
            to_email="test@proofoftalk.io",
            subject="hi",
            html="<p>hi</p>",
            force=True,
        )

    assert "tracking_options" not in captured["payload"]
```

- [ ] **Step 2: Run test, confirm failure**

Run: `cd backend && pytest tests/test_send_reengagement_email.py::test_send_email_passes_tracking_options_when_provided -v`
Expected: FAIL (unexpected keyword argument `tracking_options`).

- [ ] **Step 3: Add the parameter to `_send_email` and pipe into payload**

Edit `backend/app/services/email.py` around line 34. Change the signature:

```python
def _send_email(
    to_email: str,
    subject: str,
    html: str,
    text: str | None = None,
    attachments: list[dict] | None = None,
    force: bool = False,
    tracking_options: dict | None = None,
) -> bool:
```

And after the existing `if attachments: payload["attachments"] = attachments` block, add:

```python
    if tracking_options:
        payload["tracking_options"] = tracking_options
```

- [ ] **Step 4: Run both tests, confirm pass**

Run: `pytest tests/test_send_reengagement_email.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email.py backend/tests/test_send_reengagement_email.py
git commit -m "feat(email): _send_email supports per-call tracking_options

Optional dict passed through to Resend payload. Existing callers
unchanged (no tracking_options key in their payloads). Lays the
plumbing for the re-engagement blast template that ships next."
```

---

## Task 2: Subject-line picker + per-recipient context query

**Files:**
- Create: `backend/app/services/reengagement_blast.py`
- Test: `backend/tests/test_reengagement_blast_cohort.py` (new)

- [ ] **Step 1: Write failing tests for `pick_subject()` pure function**

Create `backend/tests/test_reengagement_blast_cohort.py`:

```python
"""Tests for the re-engagement blast cohort + subject picker."""
from app.services.reengagement_blast import pick_subject


def test_subject_with_incoming_interest_uses_reciprocity_hook():
    s = pick_subject(first_name="William", total_matches=16, incoming_interest_count=3)
    assert s == "3 people want to meet you at Proof of Talk"


def test_subject_with_one_incoming_uses_singular():
    s = pick_subject(first_name="Aylin", total_matches=22, incoming_interest_count=1)
    assert s == "1 person wants to meet you at Proof of Talk"


def test_subject_without_incoming_uses_match_count_anchor():
    s = pick_subject(first_name="William", total_matches=16, incoming_interest_count=0)
    assert s == "Your 16 matches at the Louvre, this Tuesday"


def test_subject_zero_matches_returns_none_to_signal_skip():
    s = pick_subject(first_name="William", total_matches=0, incoming_interest_count=0)
    assert s is None
```

- [ ] **Step 2: Run, confirm failure**

Run: `cd backend && pytest tests/test_reengagement_blast_cohort.py -v`
Expected: FAIL (ImportError: cannot import name 'pick_subject').

- [ ] **Step 3: Create `reengagement_blast.py` with the pure function**

Create `backend/app/services/reengagement_blast.py`:

```python
"""Re-engagement blast: cohort query + per-recipient context + subject picker.

The blast targets attendees who have a magic token but no users row
(has_account=false). Personalisation per recipient comes from total
curated+similar match count and the count of OTHER attendees who have
already marked them as a match interest.

Spec: docs/superpowers/specs/2026-05-31-reengagement-blast-design.md
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def pick_subject(
    *,
    first_name: str,
    total_matches: int,
    incoming_interest_count: int,
) -> str | None:
    """Return the subject line for this recipient, or None if no honest hook.

    - incoming interest > 0: reciprocity hook (strongest)
    - incoming = 0, matches > 0: concrete count + venue/day anchor
    - both zero: None (caller skips the send)
    """
    if total_matches == 0:
        return None
    if incoming_interest_count == 1:
        return "1 person wants to meet you at Proof of Talk"
    if incoming_interest_count > 1:
        return f"{incoming_interest_count} people want to meet you at Proof of Talk"
    return f"Your {total_matches} matches at the Louvre, this Tuesday"
```

- [ ] **Step 4: Run tests, confirm pass**

Run: `pytest tests/test_reengagement_blast_cohort.py::test_subject_with_incoming_interest_uses_reciprocity_hook tests/test_reengagement_blast_cohort.py::test_subject_with_one_incoming_uses_singular tests/test_reengagement_blast_cohort.py::test_subject_without_incoming_uses_match_count_anchor tests/test_reengagement_blast_cohort.py::test_subject_zero_matches_returns_none_to_signal_skip -v`
Expected: 4 passed.

- [ ] **Step 5: Write failing test for `RecipientContext` dataclass + cohort query**

Append to `backend/tests/test_reengagement_blast_cohort.py`:

```python
import pytest
from app.services.reengagement_blast import RecipientContext, build_cohort


@pytest.mark.asyncio
async def test_recipient_context_has_required_fields():
    """The dataclass must expose everything pick_subject + render need."""
    ctx = RecipientContext(
        attendee_id="00000000-0000-0000-0000-000000000001",
        email="x@y.com",
        first_name="X",
        magic_token="tok",
        total_matches=16,
        incoming_interest_count=2,
        top_matches=[{"name": "Y", "title": "T", "company": "C"}],
    )
    assert ctx.first_name == "X"
    assert len(ctx.top_matches) == 1
```

- [ ] **Step 6: Run, confirm failure** (ImportError on RecipientContext).

Run: `pytest tests/test_reengagement_blast_cohort.py::test_recipient_context_has_required_fields -v`

- [ ] **Step 7: Add dataclass + `build_cohort()` to `reengagement_blast.py`**

Append to `backend/app/services/reengagement_blast.py`:

```python
@dataclass
class RecipientContext:
    attendee_id: str
    email: str
    first_name: str
    magic_token: str
    total_matches: int
    incoming_interest_count: int
    top_matches: list[dict]


COHORT_SQL = text("""
SELECT
  a.id,
  a.email,
  a.name,
  a.magic_access_token,
  (
    SELECT COUNT(*) FROM matches m
    WHERE (m.attendee_a_id = a.id OR m.attendee_b_id = a.id)
      AND m.tier IN ('curated', 'priority_intro', 'similar')
  ) AS total_matches,
  (
    SELECT COUNT(*) FROM matches m
    WHERE (
      (m.attendee_a_id = a.id AND m.status_b = 'accepted')
      OR (m.attendee_b_id = a.id AND m.status_a = 'accepted')
    )
  ) AS incoming_interest_count
FROM attendees a
LEFT JOIN users u ON u.attendee_id = a.id
WHERE u.id IS NULL
  AND a.email_opt_out IS NOT TRUE
  AND a.matching_consent != 'pending'
  AND a.magic_access_token IS NOT NULL
  AND a.email NOT LIKE '%@demo.proofoftalk.io'
  AND a.email NOT LIKE '%@speaker.proofoftalk.io'
ORDER BY a.email
""")


async def build_cohort(db: AsyncSession) -> list[RecipientContext]:
    """Return one row per targetable unregistered attendee, with match context.

    Top-matches are fetched lazily by the caller via build_top_matches(); this
    function returns the lightweight subject + count row only. Keeping the
    expensive lookup separate so the cohort preview is fast.
    """
    rows = (await db.execute(COHORT_SQL)).mappings().all()
    out: list[RecipientContext] = []
    for r in rows:
        name = (r["name"] or "").strip()
        first_name = name.split()[0] if name else r["email"].split("@")[0]
        out.append(
            RecipientContext(
                attendee_id=str(r["id"]),
                email=r["email"],
                first_name=first_name,
                magic_token=r["magic_access_token"],
                total_matches=int(r["total_matches"]),
                incoming_interest_count=int(r["incoming_interest_count"]),
                top_matches=[],
            )
        )
    return out
```

- [ ] **Step 8: Run test, confirm pass**

Run: `pytest tests/test_reengagement_blast_cohort.py::test_recipient_context_has_required_fields -v`
Expected: pass.

- [ ] **Step 9: Add the `build_top_matches()` helper that fills `top_matches` for one recipient**

Append to `backend/app/services/reengagement_blast.py`:

```python
TOP_MATCHES_SQL = text("""
SELECT
  CASE WHEN m.attendee_a_id = :aid THEN m.attendee_b_id ELSE m.attendee_a_id END AS other_id,
  m.overall_score
FROM matches m
WHERE (m.attendee_a_id = :aid OR m.attendee_b_id = :aid)
  AND m.tier IN ('curated', 'priority_intro')
ORDER BY m.overall_score DESC NULLS LAST
LIMIT 2
""")


OTHER_ATTENDEE_SQL = text("""
SELECT id, name, title, company, privacy_mode
FROM attendees
WHERE id = ANY(:ids)
""")


async def fill_top_matches(db: AsyncSession, ctx: RecipientContext) -> None:
    """Hydrate ctx.top_matches with up to 2 dicts {name, title, company}.

    Privacy: b2b_only counterparts show company as name + blank title
    (mirrors send_t_minus_one_reminder_email behaviour).
    """
    rows = (await db.execute(TOP_MATCHES_SQL, {"aid": ctx.attendee_id})).mappings().all()
    if not rows:
        return
    other_ids = [str(r["other_id"]) for r in rows]
    by_id = {
        str(r["id"]): r for r in
        (await db.execute(OTHER_ATTENDEE_SQL, {"ids": other_ids})).mappings().all()
    }
    out: list[dict] = []
    for r in rows:
        other = by_id.get(str(r["other_id"]))
        if not other:
            continue
        if other["privacy_mode"] == "b2b_only":
            name = (other["company"] or "Anonymous").strip()
            title = ""
        else:
            name = (other["name"] or "").strip()
            title = (other["title"] or "").strip()
        out.append({"name": name, "title": title, "company": (other["company"] or "").strip()})
    ctx.top_matches = out
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/reengagement_blast.py backend/tests/test_reengagement_blast_cohort.py
git commit -m "feat(email): cohort query + subject picker for re-engagement blast"
```

---

## Task 3: Implement `send_reengagement_email()`

**Files:**
- Modify: `backend/app/services/email.py` (append new function)
- Test: `backend/tests/test_send_reengagement_email.py` (extend)

- [ ] **Step 1: Write failing test for the function shape**

Append to `backend/tests/test_send_reengagement_email.py`:

```python
def test_send_reengagement_email_uses_reciprocity_subject_when_incoming_gt_zero():
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        m = MagicMock()
        m.status_code = 200
        return m

    with patch.object(email_svc.httpx, "post", side_effect=fake_post):
        ok = email_svc.send_reengagement_email(
            to_email="william@blockcomp.io",
            attendee_name="William Sample",
            first_name="William",
            total_matches=16,
            incoming_interest_count=3,
            top_matches=[
                {"name": "Aylin Z", "title": "VP", "company": "Elliptic"},
                {"name": "Ylli V", "title": "CTO", "company": "Elliptic"},
            ],
            magic_token="tok_xyz",
            force=True,
        )

    assert ok is True
    assert captured["payload"]["subject"] == "3 people want to meet you at Proof of Talk"
    assert "Aylin Z" in captured["payload"]["html"]
    assert "Ylli V" in captured["payload"]["html"]
    assert "tok_xyz" in captured["payload"]["html"]
    assert captured["payload"]["tracking_options"] == {"open_tracking": True, "click_tracking": True}


def test_send_reengagement_email_uses_match_count_subject_when_no_incoming():
    captured = {}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["payload"] = json
        m = MagicMock(); m.status_code = 200; return m

    with patch.object(email_svc.httpx, "post", side_effect=fake_post):
        email_svc.send_reengagement_email(
            to_email="x@y.com",
            attendee_name="William Sample",
            first_name="William",
            total_matches=16,
            incoming_interest_count=0,
            top_matches=[{"name": "Aylin", "title": "VP", "company": "Elliptic"}],
            magic_token="tok",
            force=True,
        )
    assert captured["payload"]["subject"] == "Your 16 matches at the Louvre, this Tuesday"


def test_send_reengagement_email_returns_false_when_no_top_matches():
    """No teaser cards = no honest send."""
    with patch.object(email_svc.httpx, "post") as m_post:
        ok = email_svc.send_reengagement_email(
            to_email="x@y.com",
            attendee_name="A",
            first_name="A",
            total_matches=0,
            incoming_interest_count=0,
            top_matches=[],
            magic_token="tok",
            force=True,
        )
    assert ok is False
    assert m_post.call_count == 0
```

- [ ] **Step 2: Run, confirm failure** (AttributeError: send_reengagement_email).

Run: `pytest tests/test_send_reengagement_email.py -v`

- [ ] **Step 3: Implement `send_reengagement_email()`**

Append to `backend/app/services/email.py` (after `send_mid_event_reengagement_email`):

```python
def send_reengagement_email(
    to_email: str,
    attendee_name: str,
    first_name: str,
    total_matches: int,
    incoming_interest_count: int,
    top_matches: list[dict],
    magic_token: str,
    app_url: str | None = None,
    force: bool = False,
) -> bool:
    """Re-engagement blast for unregistered ticket-holders (2026-05-31).

    Personalised subject:
      - incoming_interest_count > 0: "N people want to meet you at Proof of Talk"
      - else, total_matches > 0:     "Your N matches at the Louvre, this Tuesday"
      - both zero: skipped (returns False)

    Body: reciprocity sentence (if applicable) + match-count anchor +
    top-2 teaser cards + "Louvre, this Tuesday" urgency. CTA deep-links
    to the magic-link page which auto-expands the claim panel.

    Resend open + click tracking is ENABLED on this template only.
    """
    from app.services.reengagement_blast import pick_subject

    settings = get_settings()
    if app_url is None:
        app_url = settings.APP_PUBLIC_URL
    if not top_matches:
        return False
    subject = pick_subject(
        first_name=first_name,
        total_matches=total_matches,
        incoming_interest_count=incoming_interest_count,
    )
    if subject is None:
        return False

    dashboard_url = f"{app_url}/m/{magic_token}"

    if incoming_interest_count == 1:
        reciprocity_line = "1 person has already said they want to meet you."
    elif incoming_interest_count > 1:
        reciprocity_line = f"{incoming_interest_count} of them have already said they want to meet you."
    else:
        reciprocity_line = ""

    cards = ""
    for i, m in enumerate(top_matches[:2], 1):
        name = (m.get("name") or "").strip() or "Top match"
        title = (m.get("title") or "").strip()
        company = (m.get("company") or "").strip()
        meta = ", ".join(x for x in (title, company) if x) or ""
        cards += (
            f"<tr><td style=\"padding:0 0 10px;\">"
            f"  <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background:#FBF8F3; border-left:3px solid #C2632A;\">"
            f"    <tr><td style=\"padding:14px 18px;\">"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:10px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; color:#C2632A; margin-bottom:6px;\">Match #{i}</div>"
            f"      <div style=\"font-family:Georgia,'Playfair Display',serif; font-size:17px; color:#211500; font-weight:600;\">{name}</div>"
            f"      <div style=\"font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:13px; color:#7A7268;\">{meta}</div>"
            f"    </td></tr>"
            f"  </table>"
            f"</td></tr>"
        )

    intro_line = (
        f"You bought a Proof of Talk ticket but haven't opened your matchmaking yet. "
        f"We've matched you with {total_matches} attendees."
    )
    if reciprocity_line:
        intro_line += " " + reciprocity_line

    body_html = _render_email(
        preheader="You haven't claimed your account yet. We've matched you with people you'll want to meet.",
        eyebrow="The Louvre, this Tuesday",
        heading=f"{first_name}, your matches are waiting",
        body_html=(
            f"<tr><td style=\"padding:0 0 14px;\">{intro_line}</td></tr>"
            f"{cards}"
            f"<tr><td style=\"padding:8px 0 4px; font-family:-apple-system,'Poppins',Arial,sans-serif; font-size:14px; color:#3A3A3A;\">The Louvre Palace. Tuesday and Wednesday. That's in 2 days.</td></tr>"
        ),
        cta_label="See who wants to meet you",
        cta_url=dashboard_url,
        unsubscribe=True,
        unsubscribe_token=magic_token,
    )
    body_text_matches = "\n".join(
        f"  Match #{i}: {m.get('name','')} - {m.get('title','')}, {m.get('company','')}"
        for i, m in enumerate(top_matches[:2], 1)
    )
    body_text = (
        f"Hi {first_name},\n\n"
        f"{intro_line}\n\n"
        f"Your top matches:\n"
        f"{body_text_matches}\n\n"
        f"The Louvre Palace. Tuesday and Wednesday. That's in 2 days.\n\n"
        f"See who wants to meet you: {dashboard_url}\n\n"
        f"Proof of Talk, The Louvre, Paris, June 2 and 3, 2026"
    )
    return _send_email(
        to_email,
        subject,
        body_html,
        body_text,
        force=force,
        tracking_options={"open_tracking": True, "click_tracking": True},
    )
```

- [ ] **Step 4: Run all tests in the file, confirm pass**

Run: `pytest tests/test_send_reengagement_email.py -v`
Expected: 5 passed.

- [ ] **Step 5: Render a sample email to disk for eyeball check**

Run:
```bash
cd backend && python3 -c "
from app.services.email import send_reengagement_email
import os
os.environ['RESEND_API_KEY'] = ''  # block actual send
# We just want the render path. Call the helpers directly:
from app.services.email import _render_email
html = _render_email(
    preheader='preview',
    eyebrow='The Louvre, this Tuesday',
    heading='William, your matches are waiting',
    body_html='<tr><td>Test body</td></tr>',
    cta_label='See who wants to meet you',
    cta_url='https://meet.proofoftalk.io/m/test',
    unsubscribe=True,
    unsubscribe_token='test',
)
open('/tmp/reengage_preview.html','w').write(html)
print('Wrote /tmp/reengage_preview.html')
"
```
Open in a browser to eyeball brand consistency. Expected: same Louvre shell as welcome.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/email.py backend/tests/test_send_reengagement_email.py
git commit -m "feat(email): send_reengagement_email with personalised subject + tracking

Subject picker:
- N>0 incoming interest: 'N people want to meet you at Proof of Talk'
- N=0, matches>0: 'Your N matches at the Louvre, this Tuesday'
- both zero: returns False (caller skips)

Resend open + click tracking enabled on this template only (via the
new tracking_options plumbing in _send_email). Existing transactional
sends untouched."
```

---

## Task 4: Operator CLI script

**Files:**
- Create: `backend/scripts/send_reengagement_blast.py`
- Reference: `backend/scripts/send_welcome_batch.py` (shape, ledger pattern, flags)

- [ ] **Step 1: Read send_welcome_batch.py end-to-end** to match its flag set, ledger format, idempotency pattern. No code change in this step.

Run: `cat backend/scripts/send_welcome_batch.py | head -80`

- [ ] **Step 2: Create the script**

Create `backend/scripts/send_reengagement_blast.py`:

```python
#!/usr/bin/env python3
"""Operator-driven re-engagement blast to unregistered ticket-holders.

Spec: docs/superpowers/specs/2026-05-31-reengagement-blast-design.md

Run from backend dir with venv activated and .env loaded:

  python scripts/send_reengagement_blast.py             # PREVIEW (default)
  python scripts/send_reengagement_blast.py --status
  python scripts/send_reengagement_blast.py --only x@y.com --confirm
  python scripts/send_reengagement_blast.py --limit 50 --confirm
  python scripts/send_reengagement_blast.py --confirm   # full blast

Idempotent via backend/exports/reengagement_sent.log (skips anyone
already in the ledger).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `app.*` importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.core.database import async_session  # noqa: E402
from app.services.email import send_reengagement_email  # noqa: E402
from app.services.reengagement_blast import (  # noqa: E402
    RecipientContext,
    build_cohort,
    fill_top_matches,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reengagement_blast")

LEDGER = Path(__file__).resolve().parents[1] / "exports" / "reengagement_sent.log"


def load_ledger() -> set[str]:
    if not LEDGER.exists():
        return set()
    return {line.split("\t", 1)[0].strip().lower() for line in LEDGER.read_text().splitlines() if line.strip()}


def append_ledger(email_addr: str) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(f"{email_addr}\t{datetime.now(timezone.utc).isoformat()}\n")


async def gather_cohort(only: str | None) -> list[RecipientContext]:
    async with async_session() as db:
        cohort = await build_cohort(db)
        if only:
            cohort = [c for c in cohort if c.email.lower() == only.lower()]
        # Sort by descending incoming_interest_count then total_matches so the
        # most-valuable-to-convert recipients send first (matters if a wave is
        # capped via --limit).
        cohort.sort(
            key=lambda c: (c.incoming_interest_count, c.total_matches),
            reverse=True,
        )
        # Top-matches lookup is per-recipient; do it serially. Cohort is
        # ~1k, ~5ms each = under 10s wall. No need to parallelise.
        for c in cohort:
            await fill_top_matches(db, c)
    return cohort


def _filter_sendable(cohort: list[RecipientContext], already_sent: set[str]) -> list[RecipientContext]:
    out: list[RecipientContext] = []
    for c in cohort:
        if c.email.lower() in already_sent:
            continue
        if c.total_matches == 0 or not c.top_matches:
            continue
        out.append(c)
    return out


def cmd_status(cohort: list[RecipientContext], already_sent: set[str]) -> None:
    sendable = _filter_sendable(cohort, already_sent)
    skipped_no_match = sum(1 for c in cohort if c.total_matches == 0 or not c.top_matches)
    skipped_already_sent = len(cohort) - len(sendable) - skipped_no_match
    print(f"Cohort size:               {len(cohort)}")
    print(f"Already in ledger:         {skipped_already_sent}")
    print(f"No matches (skip):         {skipped_no_match}")
    print(f"Sendable now:              {len(sendable)}")
    by_incoming = sum(1 for c in sendable if c.incoming_interest_count > 0)
    print(f"  with incoming interest:  {by_incoming}")
    print(f"  match-count anchor only: {len(sendable) - by_incoming}")


def cmd_preview(cohort: list[RecipientContext], already_sent: set[str], limit: int | None) -> None:
    sendable = _filter_sendable(cohort, already_sent)
    if limit:
        sendable = sendable[:limit]
    print(f"PREVIEW: would send to {len(sendable)} recipients")
    print(f"Ledger: {LEDGER}")
    print("First 5:")
    for c in sendable[:5]:
        print(
            f"  {c.email:40s} matches={c.total_matches:3d} incoming={c.incoming_interest_count:2d}"
            f" top1={(c.top_matches[0]['name'] if c.top_matches else 'NONE')[:30]}"
        )
    print("\nRe-run with --confirm to actually send.")


def cmd_confirm(cohort: list[RecipientContext], already_sent: set[str], limit: int | None) -> None:
    sendable = _filter_sendable(cohort, already_sent)
    if limit:
        sendable = sendable[:limit]
    log.info("Sending to %d recipients", len(sendable))
    sent = errors = bail_threshold = 0
    BAIL_AFTER = 100
    BAIL_RATE = 0.05  # bail if >5% errors in first 100
    for i, c in enumerate(sendable, 1):
        ok = send_reengagement_email(
            to_email=c.email,
            attendee_name=c.first_name,  # use first name as name fallback
            first_name=c.first_name,
            total_matches=c.total_matches,
            incoming_interest_count=c.incoming_interest_count,
            top_matches=c.top_matches,
            magic_token=c.magic_token,
            force=True,
        )
        if ok:
            sent += 1
            append_ledger(c.email)
        else:
            errors += 1
        if i % 25 == 0:
            log.info("Progress: %d/%d sent=%d errors=%d", i, len(sendable), sent, errors)
        if i == BAIL_AFTER and errors / BAIL_AFTER > BAIL_RATE:
            log.error("Bail: %d errors in first %d sends (>%.0f%%)", errors, BAIL_AFTER, BAIL_RATE * 100)
            break
    log.info("DONE: sent=%d errors=%d", sent, errors)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="actually send (default: preview)")
    ap.add_argument("--limit", type=int, default=None, help="wave cap")
    ap.add_argument("--only", type=str, default=None, help="single recipient smoke")
    ap.add_argument("--status", action="store_true", help="print cohort breakdown and exit")
    args = ap.parse_args()

    cohort = asyncio.run(gather_cohort(args.only))
    already_sent = load_ledger()

    if args.status:
        cmd_status(cohort, already_sent)
        return 0
    if args.confirm:
        cmd_confirm(cohort, already_sent, args.limit)
        return 0
    cmd_preview(cohort, already_sent, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Smoke-run --status in preview mode** (no sends, just confirms cohort assembly works)

Run: `cd backend && source .venv/bin/activate && python scripts/send_reengagement_blast.py --status`

Expected output shape:
```
Cohort size:               1042
Already in ledger:         0
No matches (skip):         5
Sendable now:              ~1037
  with incoming interest:  ~198
  match-count anchor only: ~839
```

If numbers diverge meaningfully from the spec, stop and reconcile.

- [ ] **Step 4: Smoke-run --preview --limit 3** (no sends, just shows the first 3)

Run: `python scripts/send_reengagement_blast.py --limit 3`

Verify the printed lines have plausible recipients + match counts + top1 names.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/send_reengagement_blast.py
git commit -m "feat(email): operator script send_reengagement_blast.py

Mirror of send_welcome_batch.py shape: preview-by-default, --confirm,
--limit, --only, --status. Separate ledger reengagement_sent.log so
the welcome ledger stays canonical for that batch.

Cohort sorted by incoming_interest DESC then total_matches DESC so
the highest-leverage recipients send first when a wave is capped.

Bail switch: stop if >5% errors in first 100 sends."
```

---

## Task 5: Single-recipient smoke send

**Why:** validate the full path end to end (render -> Resend -> inbox -> tracking pixel + click) before sending to 1,000+ people.

- [ ] **Step 1: Send `--only shaun@proofoftalk.io --confirm`**

Run from backend dir with venv active + `.env` populated (RESEND_API_KEY, DATABASE_URL, etc):
```bash
python scripts/send_reengagement_blast.py --only shaun@proofoftalk.io --confirm
```

Expected: log line "Sending to 1 recipients", "sent=1 errors=0". Ledger appends one row.

If `shaun@proofoftalk.io` doesn't appear in the cohort (he likely has a `users` row), substitute with another team email known to NOT have a users account: check via `psql` or pick one of the team allowlist domains that's not yet registered.

If no team account works as a recipient because all team are registered: temporarily seed a test attendee with the operator's address using a SQL `UPDATE attendees SET ...`, or render to disk per Task 3 Step 5 and visually inspect rather than sending.

- [ ] **Step 2: Verify the email landed in the inbox**

Open the mailbox in browser. Expected:
- Subject matches the picker rule for that recipient
- Louvre header banner renders
- Top 2 match cards render with real names
- "See who wants to meet you" CTA visible
- Footer shows Unsubscribe + Preferences

- [ ] **Step 3: Click the CTA**

The browser opens `https://meet.proofoftalk.io/m/<token>`. Expected: Phase 1-4 funnel renders the claim panel default-expanded (because `has_account=false`).

- [ ] **Step 4: Wait 5 minutes, then check Resend dashboard or query the API**

Use the same paginated query pattern from earlier this session:
```bash
RESEND_API_KEY=$(grep -E '^RESEND_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"') python3 -c "
import os, json, urllib.request
key = os.environ['RESEND_API_KEY']
req = urllib.request.Request('https://api.resend.com/emails?limit=10', headers={'Authorization': f'Bearer {key}', 'User-Agent': 'pot/1.0'})
print(json.dumps(json.loads(urllib.request.urlopen(req).read()), indent=2)[:3000])
"
```

Expected: the smoke send appears with `last_event` advancing past `delivered` to `opened` after you open the email, and to `clicked` after clicking. If `last_event` stays at `delivered` 10 minutes after opening, tracking flags are not being honoured: stop and debug Task 1 / Task 3.

- [ ] **Step 5: If tracking didn't fire, debug the payload before going wider**

Re-run `pytest tests/test_send_reengagement_email.py::test_send_email_passes_tracking_options_when_provided -v` and confirm green. Inspect the actual Resend API request via a single `httpx` call dumped to stdout. The Resend doc may have renamed the field (e.g. `tracking` instead of `tracking_options`); adjust in `email.py` and re-test.

---

## Task 6: 50-recipient deliverability wave

- [ ] **Step 1: Send the first 50**

```bash
python scripts/send_reengagement_blast.py --limit 50 --confirm
```

Expected log: `DONE: sent=50 errors=0` (or sent + errors summing to 50). Ledger grows by 50.

- [ ] **Step 2: Watch the log for the bail switch**

If the operator script prints `Bail: N errors in first 100 sends`, stop. Investigate Resend response codes from logs. Don't proceed to full blast.

- [ ] **Step 3: Wait 10 minutes, sample Resend events for the wave**

Run the Resend pagination script and confirm:
- > 96% of the 50 have `last_event` in {delivered, opened, clicked}
- 0-3 bounced (normal)
- At least some have `last_event = opened` (proves tracking is on)

- [ ] **Step 4: If green, proceed to Task 7. If red, pause and reassess.**

---

## Task 7: Full blast

- [ ] **Step 1: Send the remaining ~990**

```bash
python scripts/send_reengagement_blast.py --confirm
```

Ledger skips the 50 from Task 6 + Task 5's single smoke.

Expected: roughly 985 sent. Wall time ~15-20 min at ~1 req/s with retries.

- [ ] **Step 2: Confirm completion + final ledger size**

```bash
wc -l backend/exports/reengagement_sent.log
```

Expected: ~1,035-1,040 (one row per send).

---

## Task 8: 2-hour measurement + session log update

- [ ] **Step 1: Pull open/click stats from Resend**

Run this from `backend/` with venv active:

```bash
RESEND_API_KEY=$(grep -E '^RESEND_API_KEY=' .env | head -1 | cut -d= -f2- | tr -d '"') python3 << 'PYEOF'
import os, json, urllib.request, time, re
from collections import Counter

key = os.environ['RESEND_API_KEY']
SUBJECT_PATTERNS = [
    re.compile(r"^Your \d+ matches at the Louvre, this Tuesday$"),
    re.compile(r"^\d+ people want to meet you at Proof of Talk$"),
    re.compile(r"^1 person wants to meet you at Proof of Talk$"),
]
STOP_BEFORE = "2026-05-31"  # paginate back to before the send window

def matches_reengagement(subj: str) -> bool:
    return any(p.match(subj) for p in SUBJECT_PATTERNS)

def fetch(after=None, limit=100):
    url = f"https://api.resend.com/emails?limit={limit}"
    if after:
        url += f"&after={after}"
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}', 'User-Agent': 'pot/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

events = Counter()
rows = []
cursor = None
pages = 0
oldest = None
while True:
    pages += 1
    resp = fetch(after=cursor)
    data = resp.get('data', [])
    if not data:
        break
    for row in data:
        if matches_reengagement(row.get('subject', '')):
            events[row.get('last_event', '?')] += 1
            rows.append(row)
        oldest = row.get('created_at', '')
    if oldest and oldest < STOP_BEFORE:
        break
    if not resp.get('has_more'):
        break
    cursor = data[-1]['id']
    if pages > 50:
        break
    time.sleep(0.1)

total = len(rows)
delivered = events.get('delivered', 0) + events.get('opened', 0) + events.get('clicked', 0)
opened = events.get('opened', 0) + events.get('clicked', 0)
clicked = events.get('clicked', 0)
bounced = events.get('bounced', 0)
print(f"Re-engagement sends seen:  {total}")
print(f"Delivered or beyond:       {delivered} ({100*delivered/max(total,1):.1f}%)")
print(f"Opened or beyond:          {opened} ({100*opened/max(total,1):.1f}%)")
print(f"Clicked:                   {clicked} ({100*clicked/max(total,1):.1f}%)")
print(f"Bounced:                   {bounced} ({100*bounced/max(total,1):.1f}%)")
print()
print("Raw last_event distribution:")
for ev, c in events.most_common():
    print(f"  {ev:15s} {c}")
PYEOF
```

Record open rate, click rate, bounce rate.

- [ ] **Step 2: Pull conversion stat from DB**

Compare `users` rows created in the 2h window post-send vs the cohort:

```sql
SELECT COUNT(*) FROM users WHERE created_at >= '<send timestamp>';
```

- [ ] **Step 3: Append a topic-tagged session log entry** (per memory: parallel sessions, never wholesale-rewrite)

Append to `session_log.md`:

```
## 2026-05-31 ~XX:XX - [reengagement-blast] Shipped + measured
- Sent ~1,037 re-engagement emails to unregistered ticket-holders (has_account=false + token + not opted out + not gated + not demo + not placeholder).
- Subject variants: reciprocity ("N people want to meet you") for 198 with incoming interest; match-count anchor ("Your N matches at the Louvre, this Tuesday") for 839.
- Resend open/click tracking enabled per-template via new tracking_options plumbing on _send_email.
- 2h post-send: open rate X%, click rate Y%, registrations gained Z.
- Spec docs/superpowers/specs/2026-05-31-reengagement-blast-design.md
- Plan docs/superpowers/plans/2026-05-31-reengagement-blast-plan.md
- T-1 reminder fires tomorrow 17:00 Paris (existing cron, untouched) as natural second touch.
```

Also update `whats_next.md` Now section: move the re-engagement item to Done with the numbers.

- [ ] **Step 4: Commit the docs**

```bash
git add session_log.md whats_next.md
git commit -m "docs: re-engagement blast shipped 2026-05-31, +Z registrations in 2h"
```

---

## Spec coverage self-check

| Spec section | Covered by |
|---|---|
| Cohort definition + targeting | Task 2 (COHORT_SQL) |
| 1,042 targetable count | Task 4 Step 3 (--status sanity check) |
| 3 subject variants by recipient state | Task 2 pick_subject + Task 3 tests |
| Top-2 teaser cards | Task 3 send_reengagement_email cards loop |
| Reciprocity reveal sentence | Task 3 reciprocity_line |
| Reward-framed CTA | Task 3 cta_label="See who wants to meet you" |
| Tracking enabled per-template | Task 1 + Task 3 (`tracking_options={open_tracking, click_tracking}`) |
| Separate ledger | Task 4 (`reengagement_sent.log`) |
| Preview/confirm/limit/only/status flags | Task 4 CLI |
| Kill switch at >5% errors | Task 4 BAIL_AFTER/BAIL_RATE |
| Single-recipient smoke -> 50 wave -> full blast | Tasks 5, 6, 7 |
| 2h post-send measurement | Task 8 |
| T-1 reminder untouched | (no task; explicitly out of scope) |
| Welcome template untouched | (no task; explicitly out of scope) |

No placeholders, no TBD. Types are consistent: `RecipientContext` is defined once in Task 2 and referenced thereafter; `pick_subject()` signature is identical between Task 2 definition and Task 3 import.
