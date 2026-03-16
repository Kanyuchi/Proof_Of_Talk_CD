"""
Extasy → Live FastAPI Pipeline
================================
Fetches confirmed (PAID) attendees from the Extasy ticketing API and loads
them directly into the live app's RDS database by calling the FastAPI REST
endpoints. Optionally triggers enrichment + match generation.

Usage:
    cd backend && source .venv/bin/activate

    # Dry-run (shows what would be created, no writes):
    python scripts/pipeline_live.py --dry-run

    # Live run against production EC2:
    python scripts/pipeline_live.py

    # Run against local dev server:
    python scripts/pipeline_live.py --target local

    # Skip enrichment and match generation (just load attendees):
    python scripts/pipeline_live.py --skip-enrichment --skip-matches
"""

import argparse
import csv
import io
import os
import sys
import time
import httpx
from pathlib import Path
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ── Target API ─────────────────────────────────────────────────────────────────
TARGETS = {
    "live":  "http://3.239.218.239",   # green (active)
    "blue":  "http://54.89.55.202",    # blue (previous)
    "local": "http://localhost:8000",
}

# ── Admin credentials ──────────────────────────────────────────────────────────
ADMIN_EMAIL    = "admin@pot.demo"
ADMIN_PASSWORD = "PotAdmin2026!"

# ── Extasy API ─────────────────────────────────────────────────────────────────
EXTASY_EVENT_ID = "32b1b684-0e87-4633-92ef-b47272aa3fce"
EXTASY_BASE     = "https://api.b2b.extasy.com/operations/reports"
ORDERS_URL      = f"{EXTASY_BASE}/orders/{EXTASY_EVENT_ID}"

# ── Ticket-type mapping ────────────────────────────────────────────────────────
TICKET_TYPE_MAP = {
    "investor pass":                    "vip",
    "vip pass":                         "vip",
    "vip black pass":                   "vip",
    "general pass":                     "delegate",
    "startup pass (application based)": "delegate",
    "startup pass":                     "delegate",
    "speaker pass":                     "speaker",
    "sponsor pass":                     "sponsor",
}

TEST_TICKET_NAMES = {"test ticket", "test ticket card"}
PAID_STATUSES     = {"PAID"}
GENERIC_DOMAINS   = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}


# ── Extasy helpers ─────────────────────────────────────────────────────────────

def fetch_extasy(url: str) -> list[dict]:
    """Fetch an Extasy report endpoint. Returns list of dicts."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "csv" in content_type or "text" in content_type:
            text = resp.content.decode("iso-8859-1", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]
        try:
            return resp.json()
        except Exception:
            text = resp.content.decode("iso-8859-1", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]


def map_ticket_type(ticket_name: str) -> str:
    return TICKET_TYPE_MAP.get(ticket_name.lower().strip(), "delegate")


def is_test_ticket(ticket_name: str) -> bool:
    return ticket_name.lower().strip() in TEST_TICKET_NAMES


def build_attendee_payload(order: dict, ticket_name: str) -> dict:
    """Build the AttendeeCreate payload that the FastAPI endpoint expects."""
    first = (order.get("firstName") or "").strip()
    last  = (order.get("lastName")  or "").strip()
    name  = f"{first} {last}".strip() or "Unknown"
    email = (order.get("email") or "").strip().lower()

    company         = ""
    company_website = ""
    if email and "@" in email:
        domain = email.split("@")[1]
        if domain not in GENERIC_DOMAINS:
            company         = domain.replace("www.", "").split(".")[0].title()
            company_website = f"https://{domain}"

    return {
        "name":                  name,
        "email":                 email,
        "company":               company,
        "title":                 "",
        "ticket_type":           map_ticket_type(ticket_name),
        "interests":             [],
        "goals":                 None,
        "seeking":               [],
        "not_looking_for":       [],
        "preferred_geographies": [],
        "deal_stage":            None,
        "linkedin_url":          None,
        "twitter_handle":        None,
        "company_website":       company_website or None,
    }


def collect_records() -> list[dict]:
    """Fetch from Extasy, filter to PAID non-test, deduplicate by email."""
    print("Fetching orders from Extasy API...")
    orders = fetch_extasy(ORDERS_URL)
    print(f"  Total orders fetched: {len(orders)}")

    paid = [o for o in orders if o.get("status") in PAID_STATUSES]
    print(f"  PAID orders: {len(paid)}")

    records: list[dict] = []
    seen: set[str]      = set()

    for order in paid:
        ticket_name = (order.get("ticketNames") or "").split(",")[0].strip()

        if is_test_ticket(ticket_name):
            print(f"  SKIP (test ticket): {order.get('firstName')} {order.get('lastName')}")
            continue

        email = (order.get("email") or "").strip().lower()
        if not email:
            print(f"  SKIP (no email): {order.get('firstName')} {order.get('lastName')}")
            continue

        # Keep highest-tier ticket if same email appears twice
        if email in seen:
            existing = next(r for r in records if r["email"] == email)
            tier_order = ["delegate", "speaker", "sponsor", "vip"]
            new_tier = map_ticket_type(ticket_name)
            if tier_order.index(new_tier) > tier_order.index(existing["ticket_type"]):
                records.remove(existing)
                print(f"  UPGRADE: {email} — {existing['ticket_type']} → {new_tier}")
            else:
                continue
        else:
            seen.add(email)

        records.append(build_attendee_payload(order, ticket_name))

    print(f"\nUnique confirmed attendees: {len(records)}\n")
    return records


# ── API client ─────────────────────────────────────────────────────────────────

class LiveAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None
        self.client = httpx.Client(timeout=60)

    def close(self):
        self.client.close()

    def _auth_headers(self) -> dict:
        if not self.token:
            raise RuntimeError("Not authenticated — call login() first")
        return {"Authorization": f"Bearer {self.token}"}

    def login(self) -> None:
        resp = self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        if resp.status_code != 200:
            print(f"  ERROR: Login failed ({resp.status_code}): {resp.text}")
            sys.exit(1)
        self.token = resp.json()["access_token"]
        print("  Authenticated as admin\n")

    def list_existing_emails(self) -> set[str]:
        """Fetch all existing attendees and return their emails."""
        emails: set[str] = set()
        skip = 0
        limit = 200
        while True:
            resp = self.client.get(
                f"{self.base_url}/api/v1/attendees/",
                headers=self._auth_headers(),
                params={"skip": skip, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            attendees = data.get("attendees", [])
            for a in attendees:
                emails.add(a["email"])
            if len(attendees) < limit:
                break
            skip += limit
        return emails

    def create_attendee(self, payload: dict) -> dict | None:
        resp = self.client.post(
            f"{self.base_url}/api/v1/attendees/",
            headers=self._auth_headers(),
            json=payload,
        )
        if resp.status_code == 201:
            return resp.json()
        if resp.status_code == 409:
            return None  # already exists
        resp.raise_for_status()

    def trigger_enrichment(self) -> dict:
        """POST /api/v1/enrichment/batch — runs for all attendees."""
        resp = self.client.post(
            f"{self.base_url}/api/v1/enrichment/batch",
            headers=self._auth_headers(),
            timeout=600,  # enrichment can take a while
        )
        resp.raise_for_status()
        return resp.json()

    def trigger_match_generation(self) -> dict:
        """POST /api/v1/matches/generate-all"""
        resp = self.client.post(
            f"{self.base_url}/api/v1/matches/generate-all",
            headers=self._auth_headers(),
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()

    def get_stats(self) -> dict:
        resp = self.client.get(
            f"{self.base_url}/api/v1/dashboard/stats",
            headers=self._auth_headers(),
        )
        if resp.status_code == 200:
            return resp.json()
        return {}


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run(target: str, dry_run: bool, skip_enrichment: bool, skip_matches: bool) -> None:
    base_url = TARGETS.get(target, target)
    print(f"=== POT Matchmaker — Live Data Pipeline ===")
    print(f"Target: {base_url}")
    print(f"Mode:   {'DRY-RUN' if dry_run else 'LIVE'}\n")

    # 1. Collect records from Extasy
    records = collect_records()
    if not records:
        print("No records to process. Exiting.")
        return

    if dry_run:
        print("── DRY-RUN: Attendees that would be created ──")
        for r in records:
            print(f"  {r['name']:<30} <{r['email']}>  [{r['ticket_type']}]  {r.get('company_website') or ''}")
        print(f"\nTotal: {len(records)} attendees (no writes performed)")
        return

    # 2. Authenticate
    api = LiveAPIClient(base_url)
    print("Authenticating with live API...")
    api.login()

    # 3. Check which emails already exist
    print("Checking existing attendees in RDS...")
    existing_emails = api.list_existing_emails()
    print(f"  Already in database: {len(existing_emails)}\n")

    # 4. Create new attendees
    created  = 0
    skipped  = 0
    errors   = 0
    new_ids: list[str] = []

    print("── Loading attendees ──")
    for rec in records:
        email = rec["email"]
        name  = rec["name"]

        if email in existing_emails:
            print(f"  SKIP (exists): {name} <{email}>")
            skipped += 1
            continue

        try:
            result = api.create_attendee(rec)
            if result:
                new_ids.append(result["id"])
                print(f"  OK: {name} <{email}> [{rec['ticket_type']}]  id={result['id']}")
                created += 1
            else:
                print(f"  SKIP (409 conflict): {name} <{email}>")
                skipped += 1
        except Exception as e:
            print(f"  ERROR: {name} <{email}> — {e}")
            errors += 1

    print(f"\nLoad summary: {created} created, {skipped} skipped, {errors} errors / {len(records)} total\n")

    # 5. Enrichment
    if not skip_enrichment:
        print("── Triggering enrichment (website scraping + GPT-4o summaries + embeddings) ──")
        print("  This may take several minutes...")
        t0 = time.time()
        try:
            result = api.trigger_enrichment()
            elapsed = time.time() - t0
            enriched_count = len(result.get("results", []))
            print(f"  Enrichment completed in {elapsed:.0f}s — {enriched_count} attendees processed")
            # Show which sources were hit per attendee
            for r in result.get("results", []):
                sources = ", ".join(r.get("sources", []))
                print(f"    {r['attendee_id'][:8]}…  sources: {sources or 'none'}")
        except Exception as e:
            print(f"  ERROR during enrichment: {e}")
    else:
        print("── Skipping enrichment (--skip-enrichment) ──\n")

    # 6. Match generation
    if not skip_matches:
        print("\n── Triggering match generation (3-stage pipeline) ──")
        print("  This may take several minutes...")
        t0 = time.time()
        try:
            result = api.trigger_match_generation()
            elapsed = time.time() - t0
            total_matches = result.get("total_matches", 0)
            print(f"  Match generation completed in {elapsed:.0f}s — {total_matches} match pairs generated")
        except Exception as e:
            print(f"  ERROR during match generation: {e}")
    else:
        print("── Skipping match generation (--skip-matches) ──\n")

    # 7. Final stats
    print("\n── Final system state ──")
    try:
        stats = api.get_stats()
        if stats:
            print(f"  Total attendees:      {stats.get('total_attendees', '?')}")
            print(f"  Matches generated:    {stats.get('matches_generated', '?')}")
            print(f"  Enrichment coverage:  {stats.get('enrichment_coverage', 0):.0%}")
            print(f"  Avg match score:      {stats.get('avg_match_score', 0):.2f}")
    except Exception as e:
        print(f"  Could not fetch stats: {e}")

    print(f"\nDone. View results at: {base_url}")
    print(f"  Dashboard:  {base_url}/")
    print(f"  Attendees:  {base_url}/attendees")

    api.close()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="End-to-end pipeline: Extasy → FastAPI (RDS) → Enrichment → Matches"
    )
    parser.add_argument(
        "--target",
        default="live",
        help="'live' (default: http://3.239.218.239), 'blue' (http://54.89.55.202), 'local' (http://localhost:8000), or a full URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview attendees without making any API calls",
    )
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip the enrichment batch after loading attendees",
    )
    parser.add_argument(
        "--skip-matches",
        action="store_true",
        help="Skip match generation after enrichment",
    )
    args = parser.parse_args()

    run(
        target=args.target,
        dry_run=args.dry_run,
        skip_enrichment=args.skip_enrichment,
        skip_matches=args.skip_matches,
    )
