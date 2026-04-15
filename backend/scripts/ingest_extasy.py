"""
Extasy → Supabase ingestion script
====================================
Fetches confirmed (PAID + REDEEMED) attendees from the Extasy ticketing API
and upserts them into the Supabase attendees table.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/ingest_extasy.py

    # Dry-run (print records, no write):
    python scripts/ingest_extasy.py --dry-run

    # Force re-upsert even if record already exists:
    python scripts/ingest_extasy.py --force
"""

import argparse
import csv
import io
import os
import sys
import json
import uuid
import httpx
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    sys.exit(1)

# ── Extasy API ─────────────────────────────────────────────────────────────────
EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_BASE = "https://api.b2b.extasy.com/operations/reports"
ORDERS_URL = f"{EXTASY_BASE}/orders/{EXTASY_EVENT_ID}"
TICKETS_URL = f"{EXTASY_BASE}/tickets/{EXTASY_EVENT_ID}"

# ── Ticket-type mapping ────────────────────────────────────────────────────────
# Maps Extasy ticket name → our tickettype enum
TICKET_TYPE_MAP = {
    "investor pass":                    "VIP",
    "vip pass":                         "VIP",
    "vip black pass":                   "VIP",
    "general pass":                     "DELEGATE",
    "startup pass (application based)": "DELEGATE",
    "startup pass":                     "DELEGATE",
    "speaker pass":                     "SPEAKER",
    "sponsor pass":                     "SPONSOR",
}

# Test / internal tickets to skip
TEST_TICKET_NAMES = {"test ticket", "test ticket card"}

# Orders with these statuses are real confirmed attendees (includes complimentary tickets)
VALID_STATUSES = {"PAID", "REDEEMED"}

# Fields PATCHed onto existing rows — Rhuna/Extasy is source of truth for these.
# Never PATCH: interests, goals, seeking, enriched_profile, ai_summary, embedding,
# linkedin_url, twitter_handle — those belong to enrichment + user input.
EXTASY_PATCH_FIELDS = [
    "extasy_order_id",
    "extasy_ticket_code",
    "extasy_ticket_name",
    "phone_number",
    "city",
    "country_iso3",
    "ticket_bought_at",
    "ticket_type",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def fetch_extasy(url: str) -> list[dict]:
    """Fetch an Extasy report endpoint. Returns list of dicts (CSV or JSON)."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "csv" in content_type or "text" in content_type:
            # Decode with the charset advertised by the server
            encoding = "iso-8859-1"
            text = resp.content.decode(encoding, errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]
        # Fallback: try JSON
        try:
            return resp.json()
        except Exception:
            text = resp.content.decode("iso-8859-1", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]


def map_ticket_type(ticket_name: str) -> str:
    return TICKET_TYPE_MAP.get(ticket_name.lower().strip(), "DELEGATE")


def is_test_ticket(ticket_name: str) -> bool:
    return ticket_name.lower().strip() in TEST_TICKET_NAMES


def parse_dt(s: str) -> str | None:
    """Parse Extasy datetime string to ISO-8601 with timezone."""
    if not s:
        return None
    try:
        # Extasy returns "2026-02-12 15:52:44.692113"
        dt = datetime.fromisoformat(s.replace(" ", "T"))
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def build_attendee_record(order: dict, ticket_name: str) -> dict:
    first = (order.get("firstName") or "").strip()
    last = (order.get("lastName") or "").strip()
    name = f"{first} {last}".strip() or "Unknown"
    email = (order.get("email") or "").strip().lower()

    # Infer company name and website from email domain
    company = ""
    company_website = ""
    if email and "@" in email:
        domain = email.split("@")[1]
        # Strip common generic domains
        if domain not in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}:
            company = domain.replace("www.", "").split(".")[0].title()
            company_website = f"https://{domain}"

    enriched_profile = {
        "source": "extasy",
        "raw_order": {
            "order_id":      order.get("id"),
            "display_on":    order.get("displayOn"),
            "phone":         order.get("phoneNumber"),
            "city":          order.get("city"),
            "country_iso3":  order.get("countryIso3Code"),
            "ticket_name":   ticket_name,
            "paid_amount":   order.get("paymentsAmount"),
            "voucher_code":  order.get("voucherCode"),
        }
    }

    return {
        "id":                  str(uuid.uuid4()),
        "name":                name,
        "email":               email,
        "company":             company,
        "title":               "",
        "ticket_type":         map_ticket_type(ticket_name),
        "interests":           [],
        "goals":               None,
        "seeking":             [],
        "not_looking_for":     [],
        "preferred_geographies": [],
        "deal_stage":          None,
        "company_website":     company_website,
        "enriched_profile":    enriched_profile,
        # Extasy-specific tracking fields
        "extasy_order_id":     order.get("id"),
        "extasy_ticket_code":  (order.get("ticketCodes") or "").split(",")[0].strip(),
        "extasy_ticket_name":  ticket_name,
        "phone_number":        order.get("phoneNumber"),
        "city":                order.get("city"),
        "country_iso3":        order.get("countryIso3Code"),
        "ticket_bought_at":    parse_dt(order.get("createdAtUtc")),
    }


def upsert_to_supabase(records: list[dict], dry_run: bool, force: bool) -> None:
    """
    Insert new attendees, PATCH Extasy metadata onto existing ones.

    - New email  → POST full record
    - Existing   → PATCH only EXTASY_PATCH_FIELDS (source-of-truth from Rhuna).
                   Enriched data, interests, AI summary, etc. are preserved.
    - --force    → additionally PATCH enriched_profile with the raw Extasy
                   payload (disaster recovery; overwrites enrichment data).

    PATCHes that would be no-ops are skipped.
    """
    rest_url = f"{SUPABASE_URL}/rest/v1/attendees"
    total = len(records)
    inserted = patched = noop = errors = 0

    select_cols = "id," + ",".join(EXTASY_PATCH_FIELDS)

    with httpx.Client(timeout=30) as client:
        for rec in records:
            email = rec["email"]

            check = client.get(
                rest_url,
                headers=supabase_headers(),
                params={"email": f"eq.{email}", "select": select_cols},
            )
            if check.status_code != 200:
                print(f"  ERROR {check.status_code} lookup: <{email}> — {check.text}")
                errors += 1
                continue

            existing = check.json()

            if existing:
                existing_row = existing[0]
                desired = {k: rec[k] for k in EXTASY_PATCH_FIELDS}
                if force:
                    desired["enriched_profile"] = rec["enriched_profile"]

                diff = {k: v for k, v in desired.items() if existing_row.get(k) != v}
                if not diff:
                    print(f"  NOOP: {rec['name']} <{email}>")
                    noop += 1
                    continue

                changed = ", ".join(diff.keys())
                if dry_run:
                    print(f"  DRY-RUN PATCH: {rec['name']} <{email}> [{changed}]")
                    patched += 1
                    continue

                resp = client.patch(
                    rest_url,
                    headers={**supabase_headers(), "Prefer": "return=minimal"},
                    params={"email": f"eq.{email}"},
                    content=json.dumps(diff),
                )
                if resp.status_code in (200, 204):
                    print(f"  PATCH: {rec['name']} <{email}> [{changed}]")
                    patched += 1
                else:
                    print(f"  ERROR {resp.status_code} PATCH: <{email}> — {resp.text}")
                    errors += 1
            else:
                if dry_run:
                    print(f"  DRY-RUN INSERT: {rec['name']} <{email}> [{rec['extasy_ticket_name']}]")
                    inserted += 1
                    continue

                resp = client.post(
                    rest_url,
                    headers={**supabase_headers(), "Prefer": "return=minimal"},
                    content=json.dumps([rec]),
                )
                if resp.status_code in (200, 201):
                    print(f"  INSERT: {rec['name']} <{email}> [{rec['extasy_ticket_name']}]")
                    inserted += 1
                else:
                    print(f"  ERROR {resp.status_code} INSERT: <{email}> — {resp.text}")
                    errors += 1

    prefix = "DRY-RUN " if dry_run else ""
    print(
        f"\n{prefix}Results: {inserted} inserted, {patched} patched, "
        f"{noop} unchanged, {errors} errors / {total} total"
    )


def run(dry_run: bool, force: bool) -> None:
    print("=== POT Matchmaker — Extasy → Supabase Ingestion ===\n")

    # 1. Fetch orders
    print("Fetching orders from Extasy API...")
    orders = fetch_extasy(ORDERS_URL)
    print(f"  Total orders fetched: {len(orders)}")

    # 2. Filter to valid orders (PAID + REDEEMED)
    valid_orders = [o for o in orders if o.get("status") in VALID_STATUSES]
    print(f"  Valid orders (PAID + REDEEMED): {len(valid_orders)}")

    # 3. Build attendee records
    records = []
    seen_emails = set()

    for order in valid_orders:
        ticket_name = (order.get("ticketNames") or "").split(",")[0].strip()

        # Skip test / internal tickets
        if is_test_ticket(ticket_name):
            print(f"  SKIP (test ticket): {order.get('firstName')} {order.get('lastName')} — {ticket_name}")
            continue

        email = (order.get("email") or "").strip().lower()
        if not email:
            print(f"  SKIP (no email): {order.get('firstName')} {order.get('lastName')}")
            continue

        # Deduplicate by email — keep the highest-tier ticket
        if email in seen_emails:
            # Find existing and compare ticket tier
            existing = next(r for r in records if r["email"] == email)
            tier_order = ["DELEGATE", "SPEAKER", "SPONSOR", "VIP"]
            new_tier = map_ticket_type(ticket_name)
            if tier_order.index(new_tier) > tier_order.index(existing["ticket_type"]):
                records.remove(existing)
                print(f"  UPGRADE: {email} from {existing['ticket_type']} to {new_tier}")
            else:
                continue
        else:
            seen_emails.add(email)

        records.append(build_attendee_record(order, ticket_name))

    print(f"\nUnique confirmed attendees to ingest: {len(records)}\n")

    # 4. Show summary
    from collections import Counter
    ticket_counts = Counter(r["extasy_ticket_name"] for r in records)
    for name, count in sorted(ticket_counts.items(), key=lambda x: -x[1]):
        print(f"  {count:>3}x  {name}")
    print()

    # 5. Upsert
    upsert_to_supabase(records, dry_run=dry_run, force=force)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Extasy confirmed attendees into Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Print records without writing to Supabase")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Also PATCH enriched_profile on existing rows (disaster recovery; "
             "overwrites enrichment data with raw Extasy payload).",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, force=args.force)
