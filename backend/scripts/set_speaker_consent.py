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
