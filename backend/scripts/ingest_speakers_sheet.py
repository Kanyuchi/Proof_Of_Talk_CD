"""
Speaker Sheet → Matchmaker attendees ingest
============================================
Reads the POT26 master Speaker Tracking Google Sheet (the canonical list
maintained by Karl/PoT ops, ~144 rows) and upserts each speaker / moderator /
jury member into the `attendees` table.

Replaces the older `speakers_sync.py` path which read from the near-empty
Supabase `speakers` table managed by 1000 Minds — that table only had 8
live entries. The Google Sheet is now the source of truth.

Dedup strategy:
  1. Match by email (when present and looks real)
  2. Else match by case-insensitive name + company

Mapping:
  Category contains "Jury"       → ticket_type = VIP
  Otherwise (Speaker, Moderator) → ticket_type = SPEAKER
  Bio                            → goals
  LinkedIn URL                   → linkedin_url
  Twitter URL                    → twitter_handle (full URL — that's how the
                                   model column is used elsewhere)
  Email missing                  → placeholder `{slug}@speaker.proofoftalk.io`

Existing rows are PATCHed only with fields the sheet improves on (don't
overwrite a real Extasy email with a placeholder, don't blow away an
already-set bio with a shorter one, etc).

Usage:
    cd backend && source .venv/bin/activate
    python scripts/ingest_speakers_sheet.py --dry-run
    python scripts/ingest_speakers_sheet.py
    python scripts/ingest_speakers_sheet.py --csv data/pot_speakers_master.csv
    python scripts/ingest_speakers_sheet.py --fetch     # pull fresh from Google Sheets

The default CSV path is `backend/data/pot_speakers_master.csv`. Use --fetch
to pull a fresh copy from Google before ingesting.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    sys.exit(1)

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "pot_speakers_master.csv"
SHEET_ID = "1DJJ5vQ-t4qJli1nI5oOwy94cAY98svTQ90vTMqXceNY"
SHEET_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# Column indices in the master sheet (header is row 3, 0-indexed)
COL = {
    "id": 0,
    "first_name": 1,
    "last_name": 2,
    "company": 3,
    "title": 4,
    "category": 10,            # Speaker / Moderator / Jury / combos
    "email": 14,
    "twitter_url": 30,
    "linkedin_url": 32,
    "bio": 35,
}


def supabase_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_sheet_csv() -> str:
    """Pull the master sheet as CSV. Sheet must be link-shareable as viewer."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        resp = client.get(SHEET_EXPORT_URL)
        resp.raise_for_status()
        return resp.text


def slugify_email(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    return f"{slug}@speaker.proofoftalk.io"


PLACEHOLDER_DOMAIN = "@speaker.proofoftalk.io"


def is_placeholder(email: str) -> bool:
    return email.endswith(PLACEHOLDER_DOMAIN)


def looks_like_email(s: str) -> bool:
    s = s.strip()
    return bool(s) and "@" in s and "." in s.split("@")[-1]


def split_emails(raw: str) -> list[str]:
    """Split a sheet email cell on newlines/commas/semicolons/whitespace and
    return cleaned, valid-looking email candidates."""
    if not raw:
        return []
    parts = re.split(r"[\s,;]+", raw)
    out: list[str] = []
    for p in parts:
        cleaned = p.strip().strip(".,;:'\"").lower()
        if looks_like_email(cleaned):
            out.append(cleaned)
    return out


def email_belongs_to(email: str, first: str, last: str) -> bool:
    """Heuristic: does this email plausibly belong to a person named `first last`?

    Catches common sheet errors where an EA / colleague email landed in the
    speaker's email column. Conservative — rejects only when there is zero
    overlap with the speaker's name.
    """
    if not email or "@" not in email:
        return False
    local = email.split("@")[0].lower()
    local_alpha = re.sub(r"[^a-z]", "", local)
    f = re.sub(r"[^a-z]", "", (first or "").lower())
    l = re.sub(r"[^a-z]", "", (last or "").lower())

    # Very short alphabetic local part — accept only if it matches an initial
    # of first or last name (avoids accepting `7@x.com` typos).
    if 1 <= len(local_alpha) <= 3:
        initials = {f[:1], l[:1]} - {""}
        if local_alpha[0] in initials:
            return True
        return False

    # Direct substring of first or last name (≥3 chars each)
    if f and len(f) >= 3 and f in local_alpha:
        return True
    if l and len(l) >= 3 and l in local_alpha:
        return True

    # Common conventions: f.last, flast, first.l, firstl
    if f and l:
        if local_alpha.startswith(f[0] + l):
            return True
        if local_alpha.startswith(f + l[0]):
            return True
        if local_alpha.startswith(f + l):
            return True

    return False


def pick_speaker_email(raw: str, first: str, last: str) -> tuple[str, str | None]:
    """
    From a (possibly messy) email cell, pick the email that belongs to the
    speaker. Returns (email, suspicious_raw):
        email           — clean lowercased email, or "" if nothing usable
        suspicious_raw  — original cell value if we rejected it as wrong-person
                          (so we can record it on enriched_profile for audit)
    """
    candidates = split_emails(raw)
    if not candidates:
        return ("", None)

    # Prefer a candidate that matches the name
    for c in candidates:
        if email_belongs_to(c, first, last):
            return (c, None)

    # No candidate matched the name → reject all, flag for audit
    return ("", raw.strip() or None)


def map_ticket_type(category: str) -> str:
    cat = (category or "").lower()
    if "jury" in cat:
        return "VIP"
    return "SPEAKER"


def parse_csv(csv_text: str) -> list[dict]:
    """Parse the master sheet CSV → list of cleaned speaker dicts."""
    # StringIO (not splitlines) — preserves embedded newlines inside quoted
    # cells, which the master sheet uses to stack multiple emails per cell.
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    if len(rows) < 4:
        return []
    data_rows = rows[3:]  # rows 0-2 are merged headers / labels

    out: list[dict] = []
    for r in data_rows:
        if len(r) <= COL["last_name"]:
            continue
        rid = r[COL["id"]].strip()
        first = r[COL["first_name"]].strip()
        last = r[COL["last_name"]].strip()
        if not rid or not first:
            continue

        name = re.sub(r"\s+", " ", f"{first} {last}").strip()
        company = r[COL["company"]].strip() if len(r) > COL["company"] else ""
        title = r[COL["title"]].strip() if len(r) > COL["title"] else ""
        category = r[COL["category"]].strip() if len(r) > COL["category"] else ""
        raw_email = r[COL["email"]] if len(r) > COL["email"] else ""
        email, suspicious_email = pick_speaker_email(raw_email, first, last)
        twitter = r[COL["twitter_url"]].strip() if len(r) > COL["twitter_url"] else ""
        linkedin = r[COL["linkedin_url"]].strip() if len(r) > COL["linkedin_url"] else ""
        bio = r[COL["bio"]].strip() if len(r) > COL["bio"] else ""

        out.append({
            "sheet_id": rid,
            "name": name,
            "company": company,
            "title": title,
            "category": category,
            "email": email,
            "suspicious_email": suspicious_email,
            "twitter_url": twitter,
            "linkedin_url": linkedin,
            "bio": bio,
            "ticket_type": map_ticket_type(category),
        })
    return out


def find_existing(client: httpx.Client, speaker: dict) -> dict | None:
    """Look up an existing attendee by email, then by name+company."""
    rest = f"{SUPABASE_URL}/rest/v1/attendees"
    select = "id,name,email,company,title,ticket_type,goals,linkedin_url,twitter_handle"

    # 1. Email lookup (real email only — placeholders are not unique signals)
    if speaker["email"]:
        resp = client.get(
            rest,
            headers=supabase_headers(),
            params={"email": f"eq.{speaker['email']}", "select": select},
        )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]

    # 2. Name + company (case-insensitive) — only if name is present
    if speaker["name"]:
        params = {
            "name": f"ilike.{speaker['name']}",
            "select": select,
        }
        if speaker["company"]:
            params["company"] = f"ilike.{speaker['company']}"
        resp = client.get(rest, headers=supabase_headers(), params=params)
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]

    return None


def build_insert_record(speaker: dict) -> dict:
    email = speaker["email"] or slugify_email(speaker["name"])
    enriched: dict = {
        "source": "speakers_sheet",
        "sheet_id": speaker["sheet_id"],
        "category": speaker["category"],
    }
    if speaker.get("suspicious_email"):
        enriched["suspicious_email_in_sheet"] = speaker["suspicious_email"]
    return {
        "id": str(uuid.uuid4()),
        "name": speaker["name"],
        "email": email,
        "company": speaker["company"],
        "title": speaker["title"],
        "ticket_type": speaker["ticket_type"],
        "interests": [],
        "goals": speaker["bio"] or None,
        "seeking": [],
        "not_looking_for": [],
        "preferred_geographies": [],
        "linkedin_url": speaker["linkedin_url"] or None,
        "twitter_handle": speaker["twitter_url"] or None,
        "enriched_profile": enriched,
    }


def build_patch(speaker: dict, existing: dict) -> dict:
    """Only update fields the sheet legitimately improves."""
    patch: dict = {}

    # Ticket type — promote to SPEAKER/VIP if existing is DELEGATE/SPONSOR
    tier_order = {"DELEGATE": 0, "SPONSOR": 1, "SPEAKER": 2, "VIP": 3}
    new_tier = speaker["ticket_type"]
    cur_tier = (existing.get("ticket_type") or "DELEGATE").upper()
    if tier_order.get(new_tier, 0) > tier_order.get(cur_tier, 0):
        patch["ticket_type"] = new_tier

    # Replace placeholder email with a real one if we have it
    if speaker["email"] and is_placeholder(existing.get("email") or ""):
        patch["email"] = speaker["email"]

    # Title — fill if blank
    if speaker["title"] and not (existing.get("title") or "").strip():
        patch["title"] = speaker["title"]

    # Company — fill if blank
    if speaker["company"] and not (existing.get("company") or "").strip():
        patch["company"] = speaker["company"]

    # Bio → goals — only if longer than what's there
    if speaker["bio"]:
        cur_goals = existing.get("goals") or ""
        if len(speaker["bio"]) > len(cur_goals):
            patch["goals"] = speaker["bio"]

    # LinkedIn — fill if blank
    if speaker["linkedin_url"] and not (existing.get("linkedin_url") or "").strip():
        patch["linkedin_url"] = speaker["linkedin_url"]

    # Twitter — fill if blank
    if speaker["twitter_url"] and not (existing.get("twitter_handle") or "").strip():
        patch["twitter_handle"] = speaker["twitter_url"]

    return patch


def run(csv_path: Path, fetch: bool, dry_run: bool) -> dict:
    print("=== POT Matchmaker — Speaker Sheet → Supabase ===\n")

    # 1. Load CSV
    if fetch:
        print(f"Fetching live sheet ({SHEET_ID})...")
        csv_text = fetch_sheet_csv()
        # Save a snapshot for reproducibility
        csv_path.write_text(csv_text, encoding="utf-8")
        print(f"  saved snapshot → {csv_path}")
    else:
        print(f"Reading {csv_path}")
        csv_text = csv_path.read_text(encoding="utf-8")

    speakers = parse_csv(csv_text)
    print(f"  parsed {len(speakers)} speakers from sheet\n")

    # 2. Walk + upsert
    rest = f"{SUPABASE_URL}/rest/v1/attendees"
    inserted = patched = noop = errors = 0
    new_attendee_ids: list[str] = []

    with httpx.Client(timeout=30) as client:
        for sp in speakers:
            existing = find_existing(client, sp)

            if existing:
                patch = build_patch(sp, existing)
                if not patch:
                    noop += 1
                    continue
                changed = ", ".join(patch.keys())
                if dry_run:
                    print(f"  DRY-RUN PATCH: {sp['name']} <{existing['email']}> [{changed}]")
                    patched += 1
                    continue
                resp = client.patch(
                    rest,
                    headers={**supabase_headers(), "Prefer": "return=minimal"},
                    params={"id": f"eq.{existing['id']}"},
                    content=json.dumps(patch),
                )
                if resp.status_code in (200, 204):
                    print(f"  PATCH: {sp['name']} <{existing['email']}> [{changed}]")
                    patched += 1
                else:
                    print(f"  ERROR {resp.status_code} PATCH {sp['name']}: {resp.text}")
                    errors += 1
            else:
                rec = build_insert_record(sp)
                if dry_run:
                    placeholder_note = " [placeholder email]" if not sp["email"] else ""
                    print(f"  DRY-RUN INSERT: {rec['name']} <{rec['email']}> "
                          f"({rec['ticket_type']}){placeholder_note}")
                    inserted += 1
                    continue
                resp = client.post(
                    rest,
                    headers={**supabase_headers(), "Prefer": "return=minimal"},
                    content=json.dumps([rec]),
                )
                if resp.status_code in (200, 201):
                    print(f"  INSERT: {rec['name']} <{rec['email']}> ({rec['ticket_type']})")
                    inserted += 1
                    new_attendee_ids.append(rec["id"])
                else:
                    print(f"  ERROR {resp.status_code} INSERT {rec['name']}: {resp.text}")
                    errors += 1

    prefix = "DRY-RUN " if dry_run else ""
    print(
        f"\n{prefix}Results: {inserted} inserted, {patched} patched, "
        f"{noop} unchanged, {errors} errors / {len(speakers)} total"
    )
    return {
        "total": len(speakers),
        "inserted": inserted,
        "patched": patched,
        "noop": noop,
        "errors": errors,
        "new_ids": new_attendee_ids,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest POT speaker master sheet into matchmaker")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help="Path to local CSV snapshot (default: backend/data/pot_speakers_master.csv)")
    parser.add_argument("--fetch", action="store_true",
                        help="Pull fresh from Google Sheets and overwrite the local snapshot before ingesting")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print intended operations without writing")
    args = parser.parse_args()

    run(csv_path=args.csv, fetch=args.fetch, dry_run=args.dry_run)
