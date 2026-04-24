"""
Validate LinkedIn enrichment by comparing the scraped profile against
the registered attendee name + company.

Flags scrapes where the URL slug does not contain the attendee's first or
last name — almost always a wrong-person match from LinkedIn people-search.

Usage:
    python scripts/validate_linkedin.py           # report only
    python scripts/validate_linkedin.py --clean   # also remove bad matches
"""

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

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


def fetch_attendees_with_linkedin() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    params = {
        "select": "id,name,email,company,linkedin_url,enriched_profile",
        "linkedin_url": "not.is.null",
        "limit": "500",
    }
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=sb_headers(), params=params)
        resp.raise_for_status()
        return [a for a in resp.json() if (a.get("enriched_profile") or {}).get("linkedin")]


def normalize(s: str) -> str:
    """Lowercase, strip accents, collapse non-alphanumerics."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    return "".join(c if c.isalnum() else " " for c in s).strip()


def name_tokens(name: str) -> list[str]:
    return [t for t in normalize(name).split() if len(t) >= 3]


def validate_attendee(attendee: dict) -> tuple[str, list[str]]:
    """Return (verdict, reasons). Verdict ∈ {ok, suspicious, bad}."""
    reasons = []
    name = attendee.get("name", "")
    company = attendee.get("company", "")
    linkedin_url = unquote(attendee.get("linkedin_url", ""))
    linkedin_data = (attendee.get("enriched_profile") or {}).get("linkedin", {})
    headline = linkedin_data.get("headline", "") or ""
    experiences = linkedin_data.get("experiences", []) or []

    tokens = name_tokens(name)
    if len(tokens) < 2:
        return "ok", ["short name — skipped"]

    first, last = tokens[0], tokens[-1]

    # Extract slug
    slug_match = linkedin_url.lower().split("/in/")
    if len(slug_match) < 2:
        return "suspicious", ["no /in/ in URL"]
    slug = slug_match[1].split("?")[0].rstrip("/").lower()
    slug_tokens = [t for t in slug.replace("-", " ").replace("_", " ").split()
                   if t and not t.isdigit() and len(t) >= 3]
    slug_norm = normalize(slug.replace("-", " ").replace("_", " "))

    has_first = first in slug_norm
    has_last = last in slug_norm

    slug_no_sep = slug.replace("-", "").replace("_", "")

    # ACCEPT: abbreviation pattern 'abhiguj' for 'abhilash gujar' — starts with
    # ≥3 chars of first name, contains last-name prefix.
    if not has_first and len(first) >= 3 and slug_no_sep.startswith(first[:3]):
        if last[:3] in slug_no_sep or last in slug_no_sep:
            has_first = True
            has_last = True
            reasons.append(f"accepted abbreviation '{slug_no_sep}'")

    # ACCEPT: initial+last pattern — 'jbouteloup' (j + bouteloup), 'pjahnke',
    # 'o-antonova', 'sdewansingh'. First char is the attendee's first-name initial,
    # rest is the last name (with optional separator).
    if not has_first and has_last and slug_no_sep.startswith(first[0]):
        # The part after the initial should match the last name
        remainder = slug_no_sep[1:]
        if remainder.startswith(last) or remainder == last:
            has_first = True
            reasons.append("accepted initial+last pattern")

    # HARD FAIL: slug's first token is a *different first name* (e.g. 'fernando' for Jaime).
    # Strong signal of wrong-person match. Requires slug_first to look name-like AND
    # to not overlap with attendee's first name. Triggers even when last name IS in slug
    # (surname collisions are common).
    if slug_tokens and not has_first:
        slug_first = slug_tokens[0]
        if (
            slug_first.isalpha()
            and len(slug_first) >= 4
            and slug_first != first
            and slug_first not in first
            and first not in slug_first
            and not slug_no_sep.startswith(first[:3] if len(first) >= 3 else first)
        ):
            reasons.append(f"slug first-token '{slug_first}' ≠ attendee first name '{first}'")
            # Escape hatch: if the scraped headline mentions the attendee's last name
            # or company, the slug is thematic (not a wrong person). E.g. Richard Holmes
            # at RSK Group with slug 'mineaction' — headline mentions 'Ordnance Management'.
            headline_norm = normalize(headline)
            confirms_via_content = (
                last in headline_norm
                or (company and normalize(company) in headline_norm)
            )
            if not confirms_via_content:
                for exp in experiences:
                    exp_norm = normalize(f"{exp.get('title', '')} {exp.get('company', '')}")
                    if last in exp_norm or (company and normalize(company) in exp_norm):
                        confirms_via_content = True
                        break
            if confirms_via_content:
                return "suspicious", reasons + ["but headline/experiences match attendee's last name or company"]
            return "bad", reasons

    # HARD FAIL: attendee's first name in slug, but a DIFFERENT long surname-like token
    # appears and attendee's last name is NOT in slug. Catches 'xaviertenaqueralt' for Xavier Gomez.
    if has_first and not has_last and len(slug_tokens) >= 2:
        # Look for a surname-like token that's clearly not the attendee's
        for tok in slug_tokens[1:]:
            if (
                tok.isalpha()
                and len(tok) >= 6
                and tok != last
                and last not in tok
                and tok not in last
            ):
                # Does headline/experiences confirm the attendee's last name or company?
                headline_norm = normalize(headline)
                confirms = last in headline_norm
                if not confirms and company:
                    confirms = normalize(company) in headline_norm
                if not confirms:
                    for exp in experiences:
                        exp_norm = normalize(f"{exp.get('title', '')} {exp.get('company', '')}")
                        if last in exp_norm or (company and normalize(company) in exp_norm):
                            confirms = True
                            break
                if not confirms:
                    reasons.append(
                        f"slug contains foreign surname '{tok}' and attendee surname '{last}' "
                        "not in headline or experiences"
                    )
                    return "bad", reasons

    # Neither name token in slug → bad
    if not has_first and not has_last:
        reasons.append(f"URL slug '{slug}' contains neither '{first}' nor '{last}'")
        # Without extra evidence, treat as bad
        return "bad", reasons

    # Both tokens match
    if has_first and has_last:
        return "ok", []

    # Only first — verify via headline/experiences
    if has_first and not has_last:
        headline_norm = normalize(headline)
        if last in headline_norm:
            return "ok", ["only first in slug; last in headline"]
        if company and normalize(company) in headline_norm:
            return "ok", ["only first in slug; company in headline"]
        for exp in experiences:
            exp_norm = normalize(f"{exp.get('title', '')} {exp.get('company', '')}")
            if last in exp_norm or (company and normalize(company) in exp_norm):
                return "ok", ["only first in slug; last/company in experiences"]
        reasons.append(f"only first '{first}' in slug; last '{last}' absent from headline/experiences")
        return "suspicious", reasons

    # Only last — common for initial-based slugs like 'jbouteloup', 'pjahnke', 'o-antonova'
    if has_last and not has_first:
        headline_norm = normalize(headline)
        # Check if slug starts with an initial of the first name: 'jbouteloup' → 'j' + last
        slug_no_separators = slug.replace("-", "").replace("_", "")
        if slug_no_separators.startswith(first[0]) and last in slug_no_separators:
            return "ok", [f"initial+last slug pattern"]
        if first in headline_norm:
            return "ok", ["only last in slug; first in headline"]
        reasons.append(f"only last '{last}' in slug; first '{first}' absent from headline")
        return "suspicious", reasons

    return "ok", []


def clear_linkedin(attendee_id: str) -> bool:
    """Remove LinkedIn data from enriched_profile and clear linkedin_url."""
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    # Fetch current enriched_profile
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=sb_headers(),
            params={"id": f"eq.{attendee_id}", "select": "enriched_profile"})
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return False
        ep = rows[0].get("enriched_profile") or {}
        for k in ("linkedin", "linkedin_summary", "linkedin_enriched_at"):
            ep.pop(k, None)

        resp2 = client.patch(url,
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{attendee_id}"},
            content=json.dumps({"enriched_profile": ep, "linkedin_url": None}))
        return resp2.status_code in (200, 204)


def run(clean: bool):
    print("=== LinkedIn Enrichment Validator ===\n")
    attendees = fetch_attendees_with_linkedin()
    print(f"Found {len(attendees)} attendees with LinkedIn data\n")

    ok, suspicious, bad = [], [], []
    for a in attendees:
        verdict, reasons = validate_attendee(a)
        if verdict == "ok":
            ok.append((a, reasons))
        elif verdict == "suspicious":
            suspicious.append((a, reasons))
        else:
            bad.append((a, reasons))

    print(f"--- Results ---")
    print(f"  OK:          {len(ok):3d}")
    print(f"  Suspicious:  {len(suspicious):3d}")
    print(f"  Bad:         {len(bad):3d}")
    print()

    if bad:
        print("--- BAD MATCHES (will be cleaned with --clean) ---")
        for a, reasons in bad:
            name = a.get("name", "?")
            slug = a.get("linkedin_url", "").split("/in/")[-1].split("?")[0].rstrip("/")
            headline = ((a.get("enriched_profile") or {}).get("linkedin") or {}).get("headline", "")[:60]
            print(f"  ✗ {name:30s} | slug={slug:40s}")
            print(f"      headline: \"{headline}\"")
            print(f"      reasons: {'; '.join(reasons)}")
        print()

    if suspicious:
        print("--- SUSPICIOUS (review manually) ---")
        for a, reasons in suspicious:
            name = a.get("name", "?")
            slug = a.get("linkedin_url", "").split("/in/")[-1].split("?")[0].rstrip("/")
            headline = ((a.get("enriched_profile") or {}).get("linkedin") or {}).get("headline", "")[:60]
            print(f"  ? {name:30s} | slug={slug:40s}")
            print(f"      headline: \"{headline}\"")
            print(f"      reasons: {'; '.join(reasons)}")
        print()

    if clean and bad:
        print(f"--- Cleaning {len(bad)} BAD matches ---")
        cleaned = 0
        for a, _ in bad:
            ok_clean = clear_linkedin(a["id"])
            status = "✓" if ok_clean else "✗"
            print(f"  {status} cleaned: {a.get('name')}")
            if ok_clean:
                cleaned += 1
        print(f"\nCleaned {cleaned}/{len(bad)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate LinkedIn scrapes against registered name+company")
    parser.add_argument("--clean", action="store_true", help="Remove LinkedIn data for BAD matches")
    args = parser.parse_args()
    run(clean=args.clean)
