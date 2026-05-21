"""Staged welcome-email sender for the existing attendee pool.

Sends the branded first-touch welcome email (with each attendee's magic link)
in controlled waves. Built for launch day: lets ops blast the ~700 existing
attendees gradually — protecting deliverability (a cold-ish domain ramping up)
AND the database (clicks land on read-only /m/{token} match views) — instead of
one big-bang send.

SAFETY MODEL
------------
* Preview by default. Nothing is sent unless you pass --confirm.
* Each real send uses send_welcome_email(force=True), which bypasses the
  EMAIL_MODE gate for THIS deliberate batch only. EMAIL_MODE can stay
  "allowlist" so the automated triggers (match intros, mutual matches,
  password resets) remain gated until the team flips EMAIL_MODE=all.
* A local ledger (exports/welcome_sent.log) records every address sent, so
  reruns never double-send. (Machine-local — run all waves from one machine.
  A welcome_email_sent_at DB column would be the durable version; ledger is the
  launch-day YAGNI choice.)

EXCLUSIONS (never receive the welcome)
--------------------------------------
* email_opt_out = true           (unsubscribed)
* matching_consent in pending/declined  (gated speakers — no matches to show,
                                          no consent yet)
* no magic_access_token           (link would dump them at the login wall;
                                   run POST /matches/generate-tokens first)
* already in the ledger

USAGE
-----
    # Preview the first wave of 50 (sends nothing):
    python scripts/send_welcome_batch.py --limit 50

    # Smoke-test to specific addresses first:
    python scripts/send_welcome_batch.py --only you@proofoftalk.io --confirm

    # Send a real wave of 50:
    python scripts/send_welcome_batch.py --limit 50 --confirm

    # See how many remain to send:
    python scripts/send_welcome_batch.py --status
"""
import argparse
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.email import send_welcome_email  # noqa: E402

SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}

LEDGER = Path(__file__).resolve().parent.parent / "exports" / "welcome_sent.log"
GATED = {"pending", "declined"}


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
    """All attendees, oldest-first (stable wave ordering)."""
    rows: list[dict] = []
    offset = 0
    while True:
        r = httpx.get(
            f"{SUPA_URL}/rest/v1/attendees",
            headers=H,
            params={
                "select": "id,name,email,magic_access_token,matching_consent,email_opt_out,created_at",
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


def _classify(rows: list[dict], ledger: set[str]) -> dict:
    """Bucket every attendee into eligible / a skip reason."""
    eligible, skipped = [], {"opted_out": 0, "gated": 0, "no_token": 0, "no_email": 0, "already_sent": 0}
    for a in rows:
        email = (a.get("email") or "").strip()
        if not email:
            skipped["no_email"] += 1
            continue
        if email.lower() in ledger:
            skipped["already_sent"] += 1
            continue
        if a.get("email_opt_out"):
            skipped["opted_out"] += 1
            continue
        if (a.get("matching_consent") or "") in GATED:
            skipped["gated"] += 1
            continue
        if not a.get("magic_access_token"):
            skipped["no_token"] += 1
            continue
        eligible.append(a)
    return {"eligible": eligible, "skipped": skipped}


def _print_summary(total: int, c: dict) -> None:
    s = c["skipped"]
    print(f"  total attendees:      {total}")
    print(f"  eligible (not sent):  {len(c['eligible'])}")
    print(f"  skipped — opted out:  {s['opted_out']}")
    print(f"  skipped — gated:      {s['gated']}")
    print(f"  skipped — no token:   {s['no_token']}  (run POST /matches/generate-tokens first)")
    print(f"  skipped — no email:   {s['no_email']}")
    print(f"  skipped — already sent: {s['already_sent']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=50, help="max attendees to send this wave (default 50)")
    ap.add_argument("--confirm", action="store_true", help="actually send (default: preview only)")
    ap.add_argument("--only", action="append", default=[], help="send only to this exact email (repeatable; ignores limit/exclusions except ledger)")
    ap.add_argument("--delay", type=float, default=1.5, help="seconds between sends (default 1.5)")
    ap.add_argument("--status", action="store_true", help="print remaining-to-send counts and exit")
    args = ap.parse_args()

    if not SUPA_URL or not SUPA_KEY:
        ap.error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from .env")

    rows = _fetch_attendees()
    ledger = _load_ledger()
    classified = _classify(rows, ledger)

    if args.status:
        print("Welcome-batch status:")
        _print_summary(len(rows), classified)
        return

    # --only: target specific addresses (still respect ledger to avoid dupes)
    if args.only:
        wanted = {e.strip().lower() for e in args.only}
        targets = [a for a in rows if (a.get("email") or "").lower() in wanted]
        found = {(a.get("email") or "").lower() for a in targets}
        for miss in wanted - found:
            print(f"  ! not found in DB: {miss}")
        targets = [a for a in targets if (a.get("email") or "").lower() not in ledger]
    else:
        targets = classified["eligible"][: args.limit]

    print("Welcome-batch plan:")
    _print_summary(len(rows), classified)
    print(f"\n  this wave:            {len(targets)} {'(--only)' if args.only else f'(limit {args.limit})'}")
    print(f"  mode:                 {'SEND (force, bypasses EMAIL_MODE)' if args.confirm else 'PREVIEW (no send)'}\n")

    for a in targets[:10]:
        print(f"    -> {a['email']:<40} {a.get('name','')}")
    if len(targets) > 10:
        print(f"    … and {len(targets) - 10} more")

    if not args.confirm:
        print("\nPreview only. Re-run with --confirm to send.")
        return

    print(f"\nSending {len(targets)} welcome emails…")
    sent = failed = 0
    for i, a in enumerate(targets, 1):
        ok = send_welcome_email(
            to_email=a["email"],
            attendee_name=a.get("name") or "",
            magic_token=a.get("magic_access_token"),
            force=True,
        )
        if ok:
            sent += 1
            _append_ledger(a["email"])
            print(f"  [{i}/{len(targets)}] sent    {a['email']}")
        else:
            failed += 1
            print(f"  [{i}/{len(targets)}] FAILED  {a['email']}")
        if i < len(targets):
            time.sleep(args.delay)

    print(f"\nDone. sent={sent} failed={failed} ledger={LEDGER}")


if __name__ == "__main__":
    main()
