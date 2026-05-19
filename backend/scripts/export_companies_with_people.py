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
import pandas as pd
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

_EXPORT_DIR = Path(__file__).resolve().parents[1] / "exports"
_STAMP = f"{datetime.now():%Y%m%d}"
EXPORT_PATH = _EXPORT_DIR / f"companies_with_people_{_STAMP}.csv"
EXPORT_PATH_PEOPLE = _EXPORT_DIR / f"companies_with_people_{_STAMP}_people.csv"
EXPORT_PATH_XLSX = _EXPORT_DIR / f"companies_with_people_{_STAMP}.xlsx"

SELECT_FIELDS = (
    "name,title,email,company,ticket_type,country_iso3,linkedin_url,enriched_profile"
)


def granular_pass(row: dict) -> str:
    """Return the granular Rhuna pass name when available, falling back to
    the top-level TicketType enum.

    The top-level `ticket_type` column is a 4-value enum (DELEGATE / SPEAKER
    / VIP / SPONSOR) that collapses Rhuna's 8 granular passes (General,
    Startup, Press, Investor, VIP, VIP Black, Speaker, Sponsor). The
    granular name is preserved at `enriched_profile.extasy.ticket_name`
    on every row that came in via the Extasy sync — read it first so the
    export shows the full taxonomy, not the lossy enum.
    """
    extasy = ((row.get("enriched_profile") or {}).get("extasy") or {})
    name = (extasy.get("ticket_name") or "").strip()
    if name:
        # Trim trailing " Pass" so columns stay narrow ("VIP Black",
        # "Investor", "General"). Rhuna's own report uses the suffixed
        # form, so flagging that we stripped it would be helpful too;
        # for now this is consistent with the dashboard's display.
        return name
    enum = (row.get("ticket_type") or "").strip().upper()
    return enum


def best_position(row: dict, max_len: int = 60) -> str:
    """Return a CLEAN job title — or blank if we can't extract one.

    Sources, in priority order:
      1. attendees.title — registration-supplied
      2. enriched_profile.linkedin.experiences[0].title — formal job title
      3. enriched_profile.linkedin.headline — last resort, AFTER cleanup

    The headline source is messy: LinkedIn lets people type anything,
    so it's often "Title, Company | tagline | tagline | tagline" or a
    pasted post share. We extract just the first segment, which is
    usually the real title ("Co-Founder & CRO, Manako Labs | Your cameras
    already see it" → "Co-Founder & CRO"), and blank-out anything that
    doesn't survive the cleanup (e.g. "Catch our CEO Simone Maini on
    Bloomberg News..." stays > 60 chars → blank).

    Cleanup steps (applied to whichever source wins):
      - Newlines collapsed to single spaces.
      - Cut at the first " | " (LinkedIn multi-segment separator).
      - Cut at the first "," (separates title from company in headlines).
      - If empty or longer than max_len, blanked (still garbage).
    """
    raw = ""
    title = (row.get("title") or "").strip()
    if title:
        raw = title
    else:
        enriched = row.get("enriched_profile") or {}
        linkedin = enriched.get("linkedin") or {}
        experiences = linkedin.get("experiences") or []
        if experiences:
            raw = (experiences[0].get("title") or "").strip()
        if not raw:
            raw = (linkedin.get("headline") or "").strip()
    if not raw:
        return ""
    flat = " ".join(raw.split())
    # Pipe split: "Co-Founder | Bittensor Subnet Owner | AI | ..." → "Co-Founder"
    if "|" in flat:
        flat = flat.split("|", 1)[0].rstrip(" ,;")
    # Comma split: "Co-Founder & CRO, Manako Labs" → "Co-Founder & CRO".
    # Conservative — only the FIRST comma, so "VP, Product" stays intact
    # only if it fits in max_len; usually a comma in a headline means
    # "title, company".
    if "," in flat:
        flat = flat.split(",", 1)[0].strip()
    if not flat or len(flat) > max_len:
        return ""
    return flat


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
        if not company or not normalise(company):
            # Per Karl's request: surface these rather than hide them so the
            # export shows the full picture and where the gaps live. Bucketed
            # as a single sentinel "(no company recorded)" group at the
            # bottom of the Companies sheet.
            no_company += 1
            company = "(no company recorded)"
        key = normalise(company)
        # Dedupe within company by lowercase email; rows with no email fall
        # back to a per-row key so they aren't accidentally merged.
        member_key = (r.get("email") or f"__noemail__{id(r)}").strip().lower()
        if member_key not in groups[key]:
            groups[key][member_key] = r
        casing[key][company] += 1

    print(f"  {len(groups)} distinct companies (after normalisation)")
    print(f"  {no_company} attendees with no company recorded (grouped as '(no company recorded)')")
    print(f"  {staff_excluded} PoT/XVentures staff excluded")
    print(f"  {test_excluded} test/placeholder rows excluded\n")

    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    people_rows: list[dict] = []  # one row per person — title in its own column
    for key, members_map in groups.items():
        members = list(members_map.values())
        display = casing[key].most_common(1)[0][0]
        sorted_members = sorted(members, key=lambda m: (m.get("name") or "").lower())
        people_parts: list[str] = []
        for m in sorted_members:
            name = (m.get("name") or "").strip() or "(unknown)"
            # Companies sheet: names only — titles belong on the People sheet.
            # The previous "Name (Title); ..." format was unreadable in one cell.
            people_parts.append(name)
            # People sheet: one clean title per row, blank if we don't have a real one.
            position = best_position(m)
            email_raw = (m.get("email") or "").strip()
            email = "" if email_raw.lower().endswith("@speaker.proofoftalk.io") else email_raw
            people_rows.append({
                "company": display,
                "name": name,
                "title": position,
                "email": email,
                "ticket_type": granular_pass(m),
                "country_iso3": m.get("country_iso3") or "",
                "linkedin_url": m.get("linkedin_url") or "",
            })
        domains = sorted({
            (m.get("email") or "").split("@", 1)[1].lower()
            for m in members
            if "@" in (m.get("email") or "")
            and not (m.get("email") or "").lower().endswith("@speaker.proofoftalk.io")
        })
        ticket_types = sorted({
            granular_pass(m) for m in members if granular_pass(m)
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
    # People rows: sort by company (alphabetical), then by name within company
    people_rows.sort(key=lambda r: (r["company"].lower(), r["name"].lower()))

    header = ["company", "attendee_count", "people", "domains", "ticket_types"]
    with EXPORT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"CSV written (companies): {EXPORT_PATH}")

    # Long-format companion CSV: one row per person, title in its own
    # column so Karl can sort/filter/pivot on titles directly.
    people_header = [
        "company", "name", "title", "email",
        "ticket_type", "country_iso3", "linkedin_url",
    ]
    with EXPORT_PATH_PEOPLE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=people_header)
        writer.writeheader()
        writer.writerows(people_rows)
    print(f"CSV written (people):    {EXPORT_PATH_PEOPLE}")

    # Excel version with the same data on a "Companies" sheet plus a
    # "Summary" sheet for the exclusion/coverage stats. Same xlsxwriter
    # pattern as generate_master_ticket_file.py.
    df = pd.DataFrame(rows_out, columns=header)
    summary_df = pd.DataFrame(
        {
            "metric": [
                "Attendees in DB",
                "Distinct companies (after normalisation)",
                "Attendees with no company recorded (shown as '(no company recorded)')",
                "PoT / XVentures staff excluded",
                "Test / placeholder rows excluded",
                "Generated at",
            ],
            "value": [
                len(attendees),
                len(groups),
                no_company,
                staff_excluded,
                test_excluded,
                f"{datetime.now():%Y-%m-%d %H:%M}",
            ],
        }
    )
    people_df = pd.DataFrame(people_rows, columns=people_header)

    with pd.ExcelWriter(EXPORT_PATH_XLSX, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Companies", index=False)
        people_df.to_excel(writer, sheet_name="People", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#121212", "font_color": "#F76A0C",
            "border": 1, "align": "left", "valign": "vcenter",
        })
        wrap_fmt = workbook.add_format({"text_wrap": True, "valign": "top"})
        # Companies sheet
        ws = writer.sheets["Companies"]
        for col_num, value in enumerate(df.columns):
            ws.write(0, col_num, value, header_fmt)
        ws.set_column(0, 0, 32)
        ws.set_column(1, 1, 12)
        ws.set_column(2, 2, 80, wrap_fmt)
        ws.set_column(3, 3, 32)
        ws.set_column(4, 4, 24)
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)
        # People sheet — one row per person, title in its own column so
        # Karl can sort/filter/pivot. Per-cell wrap on the title column.
        pws = writer.sheets["People"]
        for col_num, value in enumerate(people_df.columns):
            pws.write(0, col_num, value, header_fmt)
        pws.set_column(0, 0, 32)              # company
        pws.set_column(1, 1, 26)              # name
        pws.set_column(2, 2, 60, wrap_fmt)    # title
        pws.set_column(3, 3, 30)              # email
        pws.set_column(4, 4, 12)              # ticket_type
        pws.set_column(5, 5, 10)              # country_iso3
        pws.set_column(6, 6, 40)              # linkedin_url
        pws.freeze_panes(1, 0)
        pws.autofilter(0, 0, len(people_df), len(people_df.columns) - 1)
        # Summary sheet
        sws = writer.sheets["Summary"]
        for col_num, value in enumerate(summary_df.columns):
            sws.write(0, col_num, value, header_fmt)
        sws.set_column(0, 0, 50)
        sws.set_column(1, 1, 24)
    print(f"XLSX written: {EXPORT_PATH_XLSX}\n")
    print(f"  People rows: {len(people_rows)} (one per attendee with a company)\n")
    print("── Top 10 by attendee count ────────────────────")
    for r in rows_out[:10]:
        print(f"  {r['attendee_count']:>3}  {r['company']}")
    if len(rows_out) > 10:
        print(f"       ... and {len(rows_out) - 10} more companies")


if __name__ == "__main__":
    main()
