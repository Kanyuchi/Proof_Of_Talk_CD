"""
Ticket holder export — company + position
==========================================
Pulls every attendee from Supabase that has a Rhuna ticket
(extasy_order_id is not null) and writes a CSV with the fields
Karl asked for: name, email, company, title (position), LinkedIn,
ticket type, country.

Drop the CSV straight into a Google Sheet and share.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/export_ticket_holders.py

Output:
    backend/exports/ticket_holders_company_position.csv
"""

import csv
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    sys.exit(1)

EXPORT_PATH = (
    Path(__file__).resolve().parents[1] / "exports" / "ticket_holders_company_position.csv"
)

SELECT_FIELDS = (
    "name,email,company,title,ticket_type,country_iso3,"
    "linkedin_url,twitter_handle,company_website,extasy_order_id,"
    "enriched_profile"
)


def best_position(row: dict) -> tuple[str, str]:
    """Return (position, source) — prefer registration title, fall back to
    LinkedIn headline, then experiences[0].title."""
    title = (row.get("title") or "").strip()
    if title:
        return title, "registration"
    enriched = row.get("enriched_profile") or {}
    linkedin = enriched.get("linkedin") or {}
    headline = (linkedin.get("headline") or "").strip()
    if headline:
        return headline, "linkedin_headline"
    experiences = linkedin.get("experiences") or []
    if experiences:
        exp_title = (experiences[0].get("title") or "").strip()
        if exp_title:
            return exp_title, "linkedin_experience"
    return "", ""


def fetch_ticket_holders() -> list[dict]:
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
                params={
                    "select": SELECT_FIELDS,
                    "extasy_order_id": "not.is.null",
                    "order": "company.asc,name.asc",
                },
            )
            resp.raise_for_status()
            batch = resp.json()
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    return rows


def main() -> None:
    print("=== Ticket holder export (company + position) ===\n")
    print("Fetching ticket holders from Supabase ...")
    holders = fetch_ticket_holders()
    print(f"  {len(holders)} ticket holders\n")

    header = [
        "name",
        "email",
        "company",
        "position",
        "position_source",
        "ticket_type",
        "country_iso3",
        "linkedin_url",
        "twitter_handle",
        "company_website",
    ]

    with_company = with_position = with_both = with_linkedin = 0
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EXPORT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in holders:
            company = (r.get("company") or "").strip()
            position, source = best_position(r)
            if company:
                with_company += 1
            if position:
                with_position += 1
            if company and position:
                with_both += 1
            if r.get("linkedin_url"):
                with_linkedin += 1
            writer.writerow(
                {
                    "name": r.get("name") or "",
                    "email": r.get("email") or "",
                    "company": company,
                    "position": position,
                    "position_source": source,
                    "ticket_type": r.get("ticket_type") or "",
                    "country_iso3": r.get("country_iso3") or "",
                    "linkedin_url": r.get("linkedin_url") or "",
                    "twitter_handle": r.get("twitter_handle") or "",
                    "company_website": r.get("company_website") or "",
                }
            )

    print(f"CSV written: {EXPORT_PATH}\n")
    total = len(holders) or 1
    print("── Coverage ────────────────────────────────────")
    print(f"  Has company:           {with_company:>4} / {len(holders)}  ({with_company/total:.0%})")
    print(f"  Has position:          {with_position:>4} / {len(holders)}  ({with_position/total:.0%})")
    print(f"  Has both:              {with_both:>4} / {len(holders)}  ({with_both/total:.0%})")
    print(f"  Has LinkedIn URL:      {with_linkedin:>4} / {len(holders)}  ({with_linkedin/total:.0%})")


if __name__ == "__main__":
    main()
