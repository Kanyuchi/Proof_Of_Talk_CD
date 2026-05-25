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
