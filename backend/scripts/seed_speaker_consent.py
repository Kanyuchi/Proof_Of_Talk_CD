# backend/scripts/seed_speaker_consent.py
"""Seed matching_consent='pending' for high-profile speakers flagged orange
(#f9cb9c) on column B of the '2026 - Confirmed Speakers' sheet tab, and
optionally scrub existing matches that involve a now-gated speaker.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/seed_speaker_consent.py --dry-run      # report only
    python scripts/seed_speaker_consent.py                # set pending
    python scripts/seed_speaker_consent.py --scrub-matches  # set pending + delete gated matches
"""
import argparse, json, os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SHEET_ID = "1DJJ5vQ-t4qJli1nI5oOwy94cAY98svTQ90vTMqXceNY"
CONFIRMED_TAB = "2026 - Confirmed Speakers"
ORANGE_HEX = "#f9cb9c"
SUPA_URL = os.getenv("SUPABASE_URL")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
H = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def _hexc(col) -> str:
    if not col:
        return "default"
    return "#%02x%02x%02x" % (
        round(col.get("red", 0) * 255), round(col.get("green", 0) * 255), round(col.get("blue", 0) * 255),
    )


def fetch_orange_names() -> list[str]:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    creds.refresh(Request())
    r = httpx.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}",
        params=[("ranges", f"'{CONFIRMED_TAB}'!B4:D280"),
                ("fields", "sheets(data(rowData(values(formattedValue,effectiveFormat(backgroundColor)))))")],
        headers={"Authorization": f"Bearer {creds.token}"}, timeout=40,
    )
    r.raise_for_status()
    rows = r.json()["sheets"][0]["data"][0].get("rowData", [])
    names = []
    for row in rows:
        vals = row.get("values", [])
        if not vals:
            continue
        fn = vals[0].get("formattedValue", "")
        if not fn:
            continue
        if _hexc(vals[0].get("effectiveFormat", {}).get("backgroundColor")) == ORANGE_HEX:
            ln = vals[1].get("formattedValue", "") if len(vals) > 1 else ""
            names.append(f"{fn} {ln}".strip())
    return names


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scrub-matches", action="store_true")
    args = ap.parse_args()

    orange = fetch_orange_names()
    print(f"Orange (#f9cb9c) speakers in sheet: {len(orange)}")

    att = httpx.get(f"{SUPA_URL}/rest/v1/attendees", headers=H,
                    params={"select": "id,name,matching_consent"}, timeout=60).json()
    by_name = {_norm(a["name"]): a for a in att}

    to_set, missing = [], []
    for n in orange:
        a = by_name.get(_norm(n))
        if a:
            to_set.append(a)
        else:
            missing.append(n)

    print(f"  matched in DB: {len(to_set)}   not in DB: {len(missing)} {missing}")
    if args.dry_run:
        for a in to_set:
            print(f"    would set pending: {a['name']} (now {a['matching_consent']})")
        return

    # Set pending, but never downgrade an already-granted row.
    set_ids = []
    for a in to_set:
        if a["matching_consent"] == "granted":
            print(f"    skip (already granted): {a['name']}")
            continue
        httpx.patch(f"{SUPA_URL}/rest/v1/attendees", headers=H | {"Prefer": "return=minimal"},
                    params={"id": f"eq.{a['id']}"}, json={"matching_consent": "pending"}, timeout=30)
        set_ids.append(a["id"])
    print(f"  set pending: {len(set_ids)}")

    if args.scrub_matches and set_ids:
        ids_filter = f"in.({','.join(set_ids)})"
        total = 0
        for col in ("attendee_a_id", "attendee_b_id"):
            r = httpx.delete(f"{SUPA_URL}/rest/v1/matches",
                             headers=H | {"Prefer": "return=representation"},
                             params={col: ids_filter}, timeout=60)
            total += len(r.json()) if r.status_code == 200 else 0
        print(f"  scrubbed {total} matches involving gated speakers")


if __name__ == "__main__":
    main()
