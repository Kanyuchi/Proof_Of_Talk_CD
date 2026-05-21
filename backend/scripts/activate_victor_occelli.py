"""ONE-OFF launch-day activation: create the Supabase attendees row for
Victor Occelli <victor@yelay.io>.

WHY a script and not a normal sync: Victor's ticket is a NAMED General Pass
*inside* Francisco Palminha's order 8fcd611f... (qty 2). extasy_sync dedupes
orders by BUYER email, so it created only the buyer's row and will never
create Victor's. His ticket is real + PAID, so we mint his row directly,
mirroring ingest_extasy.build_attendee_record() + the auth register flow
(magic_access_token via secrets.token_urlsafe(32)).

Activation here == data only:
  - insert attendees row (email victor@yelay.io, General Pass -> DELEGATE)
  - link the Extasy order + ticket QR under enriched_profile.extasy
  - mint magic_access_token so /m/{token} works
NO email is sent. NO match regen. Idempotent: refuses if the row already exists.

    cd backend && .venv/bin/python scripts/activate_victor_occelli.py            # dry-run
    cd backend && .venv/bin/python scripts/activate_victor_occelli.py --apply    # write
"""

import argparse
import json
import os
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing in backend/.env")
    sys.exit(1)

EMAIL = "victor@yelay.io"

# Pulled live from the Extasy /tickets feed (verified read-only):
#   ticket id   73c... -> qrCodes ZtLMs9PG, firstName Victor lastName Occelli
#   orderId     8fcd611f-254b-46d1-99d1-b5ac8380de1e (buyer: francisco@yelay.io)
ORDER_ID = "8fcd611f-254b-46d1-99d1-b5ac8380de1e"
TICKET_ID = "e09c3684-0d49-443f-808e-bde24471825b"
QR_CODE = "ZtLMs9PG"
ORDER_NUMBER = "GQxUrsWhq7"
TICKET_NAME = "General Pass"          # -> DELEGATE in our enum
BOUGHT_AT = "2026-03-16 23:33:01.526171"
PHONE = "+31611527576"
FIRST, LAST = "Victor", "Occelli"


def headers(extra: dict | None = None) -> dict:
    h = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def parse_dt(s: str) -> str | None:
    try:
        return datetime.fromisoformat(s.replace(" ", "T")).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def main(apply: bool) -> None:
    rest = f"{SUPABASE_URL}/rest/v1/attendees"

    # --- guard: refuse if a row already exists ---
    with httpx.Client(timeout=30) as client:
        check = client.get(
            rest,
            headers=headers(),
            params={"email": f"eq.{EMAIL}", "select": "id,name,email,magic_access_token"},
        )
        check.raise_for_status()
        existing = check.json()

    print("=== BEFORE STATE (Supabase lookup for victor@yelay.io) ===")
    print(json.dumps(existing, indent=2))
    print()

    if existing:
        print("ROW ALREADY EXISTS — aborting (idempotent guard). No write performed.")
        return

    token = secrets.token_urlsafe(32)
    company = "Yelay"
    record = {
        "id": str(uuid.uuid4()),
        "name": f"{FIRST} {LAST}",
        "email": EMAIL,
        "company": company,
        "title": "",
        "ticket_type": "DELEGATE",          # General Pass -> DELEGATE
        "interests": [],
        "goals": None,
        "seeking": [],
        "not_looking_for": [],
        "preferred_geographies": [],
        "deal_stage": None,
        "company_website": "https://yelay.io",
        "magic_access_token": token,
        "privacy_mode": "full",
        "enriched_profile": {
            "source": "extasy",
            "extasy": {
                "order_id": ORDER_ID,
                "ticket_id": TICKET_ID,
                "ticket_code": QR_CODE,
                "order_number": ORDER_NUMBER,
                "ticket_name": TICKET_NAME,
                "phone": PHONE,
                "country": None,
                "paid_amount": "1199.00",
                "voucher_code": None,
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "note": "Named ticket inside buyer francisco@yelay.io order; "
                        "minted manually by activate_victor_occelli.py (launch day).",
            },
        },
        "extasy_order_id": ORDER_ID,
        "ticket_bought_at": parse_dt(BOUGHT_AT),
    }

    print("=== RECORD TO INSERT ===")
    print(json.dumps(record, indent=2))
    print()

    if not apply:
        print("DRY-RUN — pass --apply to write. Nothing written.")
        print(f"(magic link would be: https://meet.proofoftalk.io/m/{token})")
        return

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            rest,
            headers=headers({"Prefer": "return=representation"}),
            content=json.dumps([record]),
        )
    if resp.status_code in (200, 201):
        print("INSERT OK")
        print(json.dumps(resp.json(), indent=2))
        print(f"\nMAGIC LINK: https://meet.proofoftalk.io/m/{token}")
    else:
        print(f"INSERT FAILED {resp.status_code}: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually write to Supabase")
    args = ap.parse_args()
    main(apply=args.apply)
