"""
Companies-with-people export for Karl
=====================================
Pulls every attendee in the matchmaker DB and groups them by company,
emitting a single CSV row per company with the people working there.

Source of "company" is `attendees.company` (registration / sheet /
ingest-supplied). We don't fall back to Grid or email-domain so the
list reflects what's actually recorded, not what we could guess.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/export_companies_with_people.py

Output:
    backend/exports/companies_with_people_YYYYMMDD.csv

Columns:
    company         Canonical display name (most common casing seen)
    attendee_count  How many people at that company are in the DB
    people          "Name (Title); Name (Title); ..." sorted alphabetically
    domains         Distinct email domains seen, "; " separated
    ticket_types    Distinct ticket types seen, "; " separated
"""

import csv
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.staff_filter import is_internal_staff  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Names that are obvious test/placeholder rows and should never reach Karl.
TEST_NAME_PATTERNS: tuple[str, ...] = ("test", "tbd", "placeholder", "demo user")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    sys.exit(1)

EXPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "exports"
    / f"companies_with_people_{datetime.now():%Y%m%d}.csv"
)

SELECT_FIELDS = "name,title,email,company,ticket_type,linkedin_url,enriched_profile"


def best_position(row: dict) -> str:
    """Same fallback chain as export_ticket_holders.py: registration title,
    then LinkedIn headline, then first LinkedIn experience title.

    Output is collapsed to a single line and truncated to 120 chars so
    Excel cells stay readable — some LinkedIn headlines turn out to be
    pasted post copy, not titles.
    """
    raw = ""
    title = (row.get("title") or "").strip()
    if title:
        raw = title
    else:
        enriched = row.get("enriched_profile") or {}
        linkedin = enriched.get("linkedin") or {}
        headline = (linkedin.get("headline") or "").strip()
        if headline:
            raw = headline
        else:
            experiences = linkedin.get("experiences") or []
            if experiences:
                raw = (experiences[0].get("title") or "").strip()
    if not raw:
        return ""
    flat = " ".join(raw.split())
    return flat if len(flat) <= 120 else flat[:117].rstrip() + "…"


def fetch_all_attendees() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    headers_base = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    page_size = 1000
    offset = 0
    rows: list[dict] = []
    with httpx.Client(timeout=30) as client:
        while True:
            headers = headers_base | {
                "Range-Unit": "items",
                "Range": f"{offset}-{offset + page_size - 1}",
            }
            resp = client.get(
                url,
                headers=headers,
                params={"select": SELECT_FIELDS, "order": "company.asc,name.asc"},
            )
            resp.raise_for_status()
            batch = resp.json()
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    return rows


def main() -> None:
    print("=== Companies-with-people export ===\n")
    print("Fetching attendees from Supabase ...")
    attendees = fetch_all_attendees()
    print(f"  {len(attendees)} attendees in DB\n")

    # Group by an aggressively-normalised key so "CertiK" + "Certik" + "Cert ik"
    # all collapse, then pick the most common original casing as the display
    # name. Within each company, dedupe people by lowercase email so a person
    # who appears twice (e.g. registered + speaker-sheet) shows up once.
    groups: dict[str, dict[str, dict]] = defaultdict(dict)
    casing: dict[str, Counter] = defaultdict(Counter)
    no_company = 0
    staff_excluded = 0
    test_excluded = 0

    def normalise(company: str) -> str:
        # Strip all non-alphanumerics so "Bitcoin Suisse" and "BitcoinSuisse"
        # collapse. False-positives are rare among real Web3 companies.
        return re.sub(r"[^a-z0-9]", "", company.lower())

    def is_test_row(name: str) -> bool:
        n = name.lower().strip()
        return any(p in n for p in TEST_NAME_PATTERNS)

    for r in attendees:
        if is_internal_staff(r):
            staff_excluded += 1
            continue
        name = (r.get("name") or "").strip()
        if is_test_row(name):
            test_excluded += 1
            continue
        company = (r.get("company") or "").strip()
        if not company:
            no_company += 1
            continue
        key = normalise(company)
        if not key:
            no_company += 1
            continue
        # Dedupe within company by lowercase email; rows with no email fall
        # back to a per-row key so they aren't accidentally merged.
        member_key = (r.get("email") or f"__noemail__{id(r)}").strip().lower()
        if member_key not in groups[key]:
            groups[key][member_key] = r
        casing[key][company] += 1

    print(f"  {len(groups)} distinct companies (after normalisation)")
    print(f"  {no_company} attendees with no company recorded (excluded)")
    print(f"  {staff_excluded} PoT/XVentures staff excluded")
    print(f"  {test_excluded} test/placeholder rows excluded\n")

    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    for key, members_map in groups.items():
        members = list(members_map.values())
        display = casing[key].most_common(1)[0][0]
        sorted_members = sorted(members, key=lambda m: (m.get("name") or "").lower())
        people_parts: list[str] = []
        for m in sorted_members:
            name = (m.get("name") or "").strip() or "(unknown)"
            position = best_position(m)
            people_parts.append(f"{name} ({position})" if position else name)
        domains = sorted({
            (m.get("email") or "").split("@", 1)[1].lower()
            for m in members
            if "@" in (m.get("email") or "")
            # Hide our synthetic placeholder domain — irrelevant to Karl.
            and not (m.get("email") or "").lower().endswith("@speaker.proofoftalk.io")
        })
        ticket_types = sorted({
            (m.get("ticket_type") or "").upper()
            for m in members
            if m.get("ticket_type")
        })
        rows_out.append({
            "company": display,
            "attendee_count": len(members),
            "people": "; ".join(people_parts),
            "domains": "; ".join(domains),
            "ticket_types": "; ".join(ticket_types),
        })

    # Sort biggest companies first, then alphabetically
    rows_out.sort(key=lambda r: (-r["attendee_count"], r["company"].lower()))

    header = ["company", "attendee_count", "people", "domains", "ticket_types"]
    with EXPORT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"CSV written: {EXPORT_PATH}\n")
    print("── Top 10 by attendee count ────────────────────")
    for r in rows_out[:10]:
        print(f"  {r['attendee_count']:>3}  {r['company']}")
    if len(rows_out) > 10:
        print(f"       ... and {len(rows_out) - 10} more companies")


if __name__ == "__main__":
    main()
