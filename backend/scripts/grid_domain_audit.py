"""
Grid coverage audit by domain
=============================
For each attendee's email domain, check if The Grid has a matching profile
(searching by URL, not by name). Returns a coverage report:

  domain.com    →   grid-slug   (grid profile name)
  other.com     →   NOT FOUND

No person-level data is touched — this is a pure domain → Grid-slug lookup.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/grid_domain_audit.py              # full audit
    python scripts/grid_domain_audit.py --csv out.csv # save to CSV
"""

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GRID_GRAPHQL_URL = "https://beta.node.thegrid.id/graphql"

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "googlemail.com", "protonmail.com", "proton.me", "pm.me", "me.com",
    "live.com", "aol.com", "msn.com",
}

# Platform / aggregator domains that can appear inside other Grid profiles' URLs
# (e.g. a Google Drive link, a Twitter profile). Matching on these is meaningless.
PLATFORM_DOMAINS = {
    "google.com", "gmail.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "linkedin.com", "youtube.com", "medium.com",
    "github.com", "notion.so", "calendly.com", "telegram.org",
    "discord.com", "discord.gg", "reddit.com",
}

# Search Grid profiles whose URLs contain a given domain substring
URL_SEARCH_QUERY = """
query SearchByUrl($pattern: String!) {
  profileInfos(
    limit: 5,
    where: {
      urls: {url: {_like: $pattern}},
      profileStatus: {slug: {_in: ["active", "announced"]}}
    }
  ) {
    id
    name
    rootId
    profileType { slug }
    profileSector { name slug }
    urls { url urlType { slug } }
  }
}
"""

# Search Grid profiles by name (for slug-style lookup from domain)
NAME_SEARCH_QUERY = """
query SearchByName($pattern: String!) {
  profileInfos(
    limit: 5,
    where: {
      name: {_like: $pattern},
      profileStatus: {slug: {_in: ["active", "announced"]}}
    }
  ) {
    id
    name
    rootId
    profileType { slug }
    profileSector { name slug }
    urls { url urlType { slug } }
  }
}
"""


def sb_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }


def fetch_domains() -> list[dict]:
    """Return [{'domain': 'x.com', 'attendee_count': N, 'has_grid': bool}]"""
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=sb_headers(),
            params={"select": "email,enriched_profile", "limit": 500})
        resp.raise_for_status()
        attendees = resp.json()

    buckets: dict[str, dict] = {}
    for a in attendees:
        email = (a.get("email") or "").lower()
        if "@" not in email:
            continue
        domain = email.split("@")[1]
        if domain in GENERIC_DOMAINS:
            continue
        ep = a.get("enriched_profile") or {}
        has_grid = bool(ep.get("grid"))
        if domain not in buckets:
            buckets[domain] = {"domain": domain, "attendee_count": 0, "has_grid": False}
        buckets[domain]["attendee_count"] += 1
        if has_grid:
            buckets[domain]["has_grid"] = True
    return sorted(buckets.values(), key=lambda x: x["domain"])


def _domain_to_slug_candidates(domain: str) -> list[str]:
    """Generate slug candidates from a domain.
    sundaebar.ai → ['sundaebar', 'sundae bar']  (not 'sundae' — too ambiguous)
    cardanofoundation.org → ['cardanofoundation', 'cardano foundation']

    Deliberately NOT doing:
      - prefix-only ('sundae', 'cardano') — too ambiguous, matched wrong Grid profiles
      - TLD stripping ('aztecai' → 'aztec', 'babslabs' → 'babs') — strips meaningful brand
    """
    # Strip TLD (everything after first dot)
    stem = domain.split(".")[0].lower()
    if not stem or len(stem) < 3:
        return []

    candidates = [stem]

    # Try splitting on known compound words — but keep BOTH parts together
    compounds = (
        "foundation", "digital", "labs", "protocol", "network", "finance",
        "capital", "ventures", "assets", "exchange", "technology", "technologies",
        "solutions", "group", "holdings", "wealth", "bar", "bit", "bank",
    )
    for suffix in compounds:
        if stem.endswith(suffix) and len(stem) > len(suffix) + 2:
            prefix = stem[: -len(suffix)]
            if len(prefix) >= 3:
                candidates.append(f"{prefix} {suffix}")
                break

    # Dedup preserving order
    seen = set()
    out = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _normalize_for_compare(s: str) -> str:
    """Collapse to lowercase alnum-only for strict equality checks.
    'Sundae Bar' → 'sundaebar', 'sundae_bar' → 'sundaebar'
    """
    return "".join(c for c in s.lower() if c.isalnum())


async def _query_grid(client: httpx.AsyncClient, query: str, pattern: str) -> list[dict]:
    """Run a Grid GraphQL query with case variants."""
    for variant in (pattern, pattern.lower(), pattern.title()):
        try:
            resp = await client.post(
                GRID_GRAPHQL_URL,
                json={"query": query, "variables": {"pattern": f"%{variant}%"}},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                continue
            results = (data.get("data") or {}).get("profileInfos") or []
            if results:
                return results
        except Exception:
            continue
    return []


def _format_match(profile: dict, matched_url: str | None, strategy: str) -> dict:
    name = profile.get("name") or ""
    slug = name.lower().replace(" ", "_")
    sector = (profile.get("profileSector") or {}).get("name", "")
    return {
        "grid_slug": slug,
        "grid_name": name,
        "grid_profile_url": f"https://thegrid.id/profiles/{slug}",
        "matched_url": matched_url or "",
        "profile_type": (profile.get("profileType") or {}).get("slug"),
        "sector": sector,
        "match_strategy": strategy,
    }


async def search_grid_by_domain(client: httpx.AsyncClient, domain: str) -> dict | None:
    """Search Grid for a profile matching this domain, using two strategies:
    1. URL-contains: Grid profile URL contains the domain substring (not for platform domains).
    2. Slug match: Grid profile name, when alnum-normalized, equals the domain stem
       (or a word-split variant). No token-subset matching — too loose.
    Strategy 1 wins if URL genuinely contains the domain.
    """
    # Strategy 1: URL contains domain (skip platform domains — they appear in other profiles)
    if domain.lower() not in PLATFORM_DOMAINS:
        results = await _query_grid(client, URL_SEARCH_QUERY, domain)
        for profile in results:
            for u in (profile.get("urls") or []):
                url_str = (u.get("url") or "").lower()
                if domain.lower() in url_str:
                    return _format_match(profile, u.get("url"), "url_contains")

    # Strategy 2: domain-stem → Grid profile name, strict normalized-equality only
    # (skip platform domains — someone @google.com isn't representing "Google" for Web3 matching)
    if domain.lower() in PLATFORM_DOMAINS:
        return None
    stem = domain.split(".")[0].lower()
    stem_norm = _normalize_for_compare(stem)
    for candidate in _domain_to_slug_candidates(domain):
        results = await _query_grid(client, NAME_SEARCH_QUERY, candidate)
        for profile in results:
            grid_name_norm = _normalize_for_compare(profile.get("name") or "")
            if not grid_name_norm:
                continue
            # Only accept exact alnum-normalized equality to the ORIGINAL stem.
            # 'sundae_bar' == 'sundaebar' → match
            # 'aztec' != 'aztecai' → rejected
            if grid_name_norm == stem_norm:
                return _format_match(profile, None, f"slug_exact:{candidate}")

    return None


async def audit(csv_path: str | None) -> None:
    print("=== Grid Domain Coverage Audit ===\n")
    domains = fetch_domains()
    print(f"Unique non-generic domains: {len(domains)}\n")

    results = []
    async with httpx.AsyncClient(timeout=20) as client:
        for i, d in enumerate(domains, 1):
            domain = d["domain"]
            match = await search_grid_by_domain(client, domain)
            row = {
                "domain": domain,
                "attendee_count": d["attendee_count"],
                "had_grid_before": d["has_grid"],
                "grid_slug": match["grid_slug"] if match else "",
                "grid_name": match["grid_name"] if match else "",
                "grid_profile_url": match["grid_profile_url"] if match else "",
                "matched_url": match["matched_url"] if match else "",
                "profile_type": match["profile_type"] if match else "",
                "sector": match["sector"] if match else "",
                "match_strategy": match["match_strategy"] if match else "",
            }
            results.append(row)

            status = "✓" if match else "✗"
            if match:
                print(f"  [{i:3d}/{len(domains)}] {status} {domain:40s} → {match['grid_slug']:30s} [{match['match_strategy']}]")
            else:
                print(f"  [{i:3d}/{len(domains)}] {status} {domain:40s} → NOT FOUND")

            # Be polite to the Grid API
            await asyncio.sleep(0.5)

    # Summary
    found = sum(1 for r in results if r["grid_slug"])
    missing = len(results) - found
    print(f"\n--- Summary ---")
    print(f"  Found in Grid:    {found}/{len(results)} ({found/len(results)*100:.0f}%)")
    print(f"  Not in Grid:      {missing}/{len(results)}")
    print(f"  Attendees covered: {sum(r['attendee_count'] for r in results if r['grid_slug'])}/{sum(r['attendee_count'] for r in results)}")

    # New matches (domain found but had_grid_before=False)
    new_matches = [r for r in results if r["grid_slug"] and not r["had_grid_before"]]
    if new_matches:
        print(f"\n--- New coverage opportunities ({len(new_matches)}) ---")
        print(f"  (domains that resolve to Grid but weren't matched by name)")
        for r in new_matches:
            print(f"    {r['domain']:40s} → {r['grid_slug']}")

    if csv_path:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"\nCSV written to: {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit Grid coverage by email domain")
    parser.add_argument("--csv", help="Optional CSV output path")
    args = parser.parse_args()
    asyncio.run(audit(args.csv))
