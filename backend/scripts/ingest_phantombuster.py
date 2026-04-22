"""
Ingest PhantomBuster LinkedIn Search results into Supabase.
==============================================================
Reads the CSV output from PhantomBuster's "LinkedIn Search to Profile Data"
phantom, matches each result to an attendee in Supabase by name/company,
and patches the LinkedIn enrichment data.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/ingest_phantombuster.py /path/to/result.csv
    python scripts/ingest_phantombuster.py /path/to/result.csv --dry-run
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    sys.exit(1)


def sb_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_attendees() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            url,
            headers=sb_headers(),
            params={
                "select": "id,name,email,company,title,linkedin_url,enriched_profile,photo_url",
                "order": "created_at.asc",
                "limit": "500",
            },
        )
        resp.raise_for_status()
        return resp.json()


def patch_attendee(aid: str, payload: dict, dry_run: bool) -> bool:
    if dry_run:
        return True
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.patch(
            url,
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{aid}"},
            content=json.dumps(payload),
        )
        return resp.status_code in (200, 204)


def extract_search_name(query_url: str) -> str:
    """Extract the name+company from a PhantomBuster search URL."""
    if "keywords=" in query_url:
        raw = query_url.split("keywords=")[1]
        return urllib.parse.unquote(raw).strip()
    return ""


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_attendee(pb_row: dict, attendees: list[dict]) -> dict | None:
    """Find the best matching attendee for a PhantomBuster result."""
    search_term = extract_search_name(pb_row.get("query", ""))
    pb_name = (pb_row.get("fullName") or "").strip().lower()
    pb_company = (pb_row.get("companyName") or "").strip().lower()

    best = None
    best_score = 0

    for att in attendees:
        att_name = (att.get("name") or "").strip().lower()
        att_company = (att.get("company") or "").strip().lower()
        att_name_norm = normalize(att_name)

        score = 0

        # Name match (required — at least partial)
        name_parts = att_name.split()
        pb_name_parts = pb_name.split()
        matching_parts = sum(1 for p in name_parts if any(p in pp for pp in pb_name_parts) and len(p) > 2)

        if matching_parts == 0:
            continue

        score += matching_parts * 2

        # Company match (strong signal)
        if att_company and pb_company:
            if normalize(att_company) in normalize(pb_company) or normalize(pb_company) in normalize(att_company):
                score += 3

        # Search term contained the attendee name
        if att_name_norm in normalize(search_term):
            score += 1

        if score > best_score:
            best_score = score
            best = att

    # Require at least a name match + company match for confidence
    if best_score >= 3:
        return best
    return None


def run(csv_path: str, dry_run: bool):
    print("=== PhantomBuster LinkedIn → Supabase Ingestion ===\n")

    # Read PhantomBuster CSV
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    found = [r for r in rows if r.get("fullName") and r["fullName"].strip()]
    print(f"  CSV rows: {len(rows)} ({len(found)} with profile data)\n")

    if not found:
        print("No profiles found in CSV.")
        return

    # Fetch attendees from Supabase
    attendees = fetch_attendees()
    print(f"  Attendees in DB: {len(attendees)}\n")

    matched = 0
    patched = 0
    skipped = 0
    ambiguous = 0

    for pb in found:
        pb_name = pb.get("fullName", "").strip()
        pb_headline = pb.get("headline", "").strip()
        pb_url = pb.get("linkedInUrl", "").strip()

        att = match_attendee(pb, attendees)

        if not att:
            print(f"  ⚠ No match: {pb_name} ({pb_headline[:40]})")
            skipped += 1
            continue

        att_name = att["name"]
        matched += 1

        # Build LinkedIn enrichment payload
        linkedin_data = {
            "headline": pb.get("headline"),
            "summary": pb.get("summary"),
            "experiences": [],
            "skills": [],
            "education": [],
            "profile_pic_url": pb.get("profilePictureUrl"),
            "source": "phantombuster",
            "location": pb.get("location"),
            "connection_degree": pb.get("connectionDegree"),
            "followers": pb.get("followersCount"),
            "company_name": pb.get("companyName"),
            "job_title": pb.get("jobTitle"),
            "industry": pb.get("industry"),
        }

        # Build enriched_profile update
        enriched = dict(att.get("enriched_profile") or {})
        enriched["linkedin"] = linkedin_data
        enriched["linkedin_enriched_at"] = datetime.now(timezone.utc).isoformat()

        # Build summary
        summary_parts = []
        if linkedin_data.get("headline"):
            summary_parts.append(linkedin_data["headline"])
        if linkedin_data.get("summary"):
            summary_parts.append(linkedin_data["summary"][:200])
        enriched["linkedin_summary"] = " | ".join(summary_parts)

        patch_payload = {
            "enriched_profile": enriched,
            "linkedin_url": pb_url or att.get("linkedin_url"),
        }

        # Auto-fill title if empty
        if not att.get("title") and linkedin_data.get("job_title"):
            patch_payload["title"] = linkedin_data["job_title"]

        # Auto-fill photo
        if linkedin_data.get("profile_pic_url") and not att.get("photo_url"):
            patch_payload["photo_url"] = linkedin_data["profile_pic_url"]

        label = "DRY" if dry_run else "OK"
        print(f"  ✅ {att_name:30s} ← {pb_name} | {pb_headline[:40]}")

        ok = patch_attendee(att["id"], patch_payload, dry_run)
        if ok:
            patched += 1
        else:
            print(f"    ❌ Supabase patch failed")

    prefix = "DRY-RUN " if dry_run else ""
    print(f"\n{prefix}Done: {matched} matched, {patched} patched, {skipped} no match, {ambiguous} ambiguous / {len(found)} profiles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PhantomBuster LinkedIn results into Supabase")
    parser.add_argument("csv_path", help="Path to PhantomBuster result CSV")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    run(csv_path=args.csv_path, dry_run=args.dry_run)
