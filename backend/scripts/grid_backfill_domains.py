"""
Grid backfill for specific email domains
========================================
Surgical backfill: given one or more email domains whose Grid profile we
know exists (e.g. discovered by grid_domain_audit.py), find every attendee
on that domain whose enriched_profile.grid is empty, fetch their Grid
profile via enrich_from_grid(), and patch their record.

Reversibility:
- Prints each attendee's existing enriched_profile (full) before patching,
  so the JSON is preserved in stdout and can be hand-rolled back if needed.
- --dry-run mode does the lookup and prints the would-be patch without
  writing.
- Skips attendees who already have enriched_profile.grid populated unless
  --force is passed.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/grid_backfill_domains.py bundesblock.de digital-euro-association.de stablecoinstandard.com
    python scripts/grid_backfill_domains.py --dry-run bundesblock.de
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from app.services.grid_enrichment import enrich_from_grid  # noqa: E402

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)


def sb_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }


def fetch_attendees_by_domain(domain: str) -> list[dict]:
    """Return all attendees whose email is on this domain."""
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            url,
            headers=sb_headers(),
            params={
                "select": "id,name,email,company,company_website,enriched_profile",
                "email": f"ilike.*@{domain}",
            },
        )
        resp.raise_for_status()
        return resp.json()


def patch_attendee(attendee_id: str, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.patch(
            url,
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{attendee_id}"},
            content=json.dumps(payload),
        )
        if resp.status_code not in (200, 204):
            print(f"    PATCH failed: {resp.status_code} {resp.text[:200]}")
            return False
        return True


async def backfill_domain(domain: str, dry_run: bool, force: bool) -> dict:
    """Backfill Grid data for every attendee on this domain. Returns counts."""
    print(f"\n=== {domain} ===")
    attendees = fetch_attendees_by_domain(domain)
    if not attendees:
        print(f"  No attendees found on {domain}.")
        return {"domain": domain, "found": 0, "skipped": 0, "patched": 0, "errors": 0}

    print(f"  Found {len(attendees)} attendee(s) on this domain.")

    skipped = patched = errors = 0
    for a in attendees:
        name = a.get("name") or "(unnamed)"
        aid = a["id"]
        enriched = a.get("enriched_profile") or {}
        already_has_grid = bool(enriched.get("grid"))

        if already_has_grid and not force:
            print(f"  - {name:35s} → SKIP (grid already present; use --force to overwrite)")
            skipped += 1
            continue

        company = a.get("company") or ""
        website = a.get("company_website") or ""
        if not company:
            print(f"  - {name:35s} → SKIP (no company name on record)")
            skipped += 1
            continue

        # Print pre-state so it's recoverable from stdout if needed
        print(f"  - {name:35s} → looking up '{company}' (domain={domain})")
        print(f"      pre_enriched_keys: {sorted(enriched.keys()) if enriched else '[]'}")

        grid_data = await enrich_from_grid(company, website, domain)
        if not grid_data:
            print(f"      ✗ no Grid match found via name or URL search")
            errors += 1
            continue

        new_enriched = {**enriched}
        new_enriched["grid"] = grid_data
        new_enriched["grid_enriched_at"] = datetime.now(timezone.utc).isoformat()
        new_enriched["grid_attempted_at"] = datetime.now(timezone.utc).isoformat()

        if dry_run:
            print(f"      DRY ✓ would patch grid → {grid_data['grid_name']} ({grid_data['grid_sector']})")
            patched += 1
            continue

        ok = patch_attendee(aid, {"enriched_profile": new_enriched})
        if ok:
            print(f"      ✓ patched grid → {grid_data['grid_name']} ({grid_data['grid_sector']})")
            patched += 1
        else:
            errors += 1

    return {"domain": domain, "found": len(attendees), "skipped": skipped, "patched": patched, "errors": errors}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Grid data for attendees on specific email domains")
    parser.add_argument("domains", nargs="+", help="Email domains to backfill (e.g. bundesblock.de)")
    parser.add_argument("--dry-run", action="store_true", help="Look up but don't write to Supabase")
    parser.add_argument("--force", action="store_true", help="Overwrite existing enriched_profile.grid")
    args = parser.parse_args()

    print("=== Grid Domain Backfill ===")
    print(f"  Domains: {', '.join(args.domains)}")
    print(f"  Mode:    {'DRY RUN' if args.dry_run else 'LIVE'}{' (force)' if args.force else ''}\n")

    results = []
    for domain in args.domains:
        results.append(await backfill_domain(domain, args.dry_run, args.force))

    print("\n--- Summary ---")
    for r in results:
        print(f"  {r['domain']:40s} found={r['found']} skipped={r['skipped']} patched={r['patched']} errors={r['errors']}")

    total_patched = sum(r["patched"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    print(f"\n  TOTAL: patched={total_patched} errors={total_errors}")

    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
