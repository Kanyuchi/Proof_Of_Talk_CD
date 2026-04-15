"""
The Grid B2B Enrichment
=======================
Queries The Grid (thegrid.id) GraphQL API for verified Web3 company data.
No authentication required — API is publicly accessible.

Fetches: profile info (logo, description, sector, socials), products, and entities.

Endpoint: https://beta.node.thegrid.id/graphql
Explorer: https://cloud.hasura.io/public/graphiql?endpoint=https://beta.node.thegrid.id/graphql

Resilience:
- Retries with backoff on transient failures (timeout, 5xx)
- Case-insensitive search workaround (_like with multiple case variants)
- GraphQL errors logged explicitly (not swallowed)
- health_check() function to verify API before event
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

GRID_GRAPHQL_URL = "https://beta.node.thegrid.id/graphql"

# Retry settings
MAX_RETRIES = 2
RETRY_BACKOFF = [1.0, 3.0]  # seconds between retries

# Stage 1: Find the profile and get rootId for cross-entity queries
# NOTE: _ilike was removed from the Grid API around April 2026.
# _like is case-sensitive, so we search with multiple case variants.
PROFILE_QUERY = """
query SearchCompany($name: String!) {
  profileInfos(limit: 3, where: {name: {_like: $name}, profileStatus: {slug: {_eq: "active"}}}) {
    id
    name
    rootId
    tagLine
    descriptionShort
    descriptionLong
    profileType { name slug }
    profileSector { name slug }
    foundingDate
    media { url mediaType { name slug } }
    urls { url urlType { name slug } }
    socials { name socialType { name slug } urls { url } }
  }
}
"""

# Stage 2: Fetch products + entities by rootId
DETAILS_QUERY = """
query OrgDetails($rootId: String!) {
  products(limit: 10, where: {rootId: {_eq: $rootId}}) {
    name
    description
    productType { name slug }
    isMainProduct
  }
  entities(limit: 5, where: {rootId: {_eq: $rootId}}) {
    name
    tradeName
    entityType { name slug }
    country { name }
    dateOfIncorporation
  }
}
"""


async def health_check() -> dict:
    """
    Verify the Grid API is reachable and the schema we depend on still works.
    Returns {"ok": True/False, "profiles_count": N, "error": "..."}.
    Call this before the event and in monitoring.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 1. Basic connectivity
            resp = await client.post(
                GRID_GRAPHQL_URL,
                json={"query": '{ profileInfos(limit: 1) { id name } }'},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                return {"ok": False, "error": f"GraphQL schema error: {data['errors'][0]['message']}"}

            profiles = (data.get("data") or {}).get("profileInfos") or []
            if not profiles:
                return {"ok": False, "error": "API returned 0 profiles — data may be missing"}

            # 2. Verify _like filter still works (our search depends on it)
            resp2 = await client.post(
                GRID_GRAPHQL_URL,
                json={"query": PROFILE_QUERY, "variables": {"name": "%Kraken%"}},
                headers={"Content-Type": "application/json"},
            )
            data2 = resp2.json()
            if data2.get("errors"):
                return {"ok": False, "error": f"_like filter broken: {data2['errors'][0]['message']}"}

            found = (data2.get("data") or {}).get("profileInfos") or []
            if not found:
                return {"ok": False, "error": "_like filter returned no results for 'Kraken' — search may be broken"}

            return {"ok": True, "profiles_count": len(profiles), "test_search": found[0]["name"]}

    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"HTTP error: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"Unexpected: {exc}"}


# Generic business-suffix words that are TOO weak to match on alone.
# "Ventures", "capital", "labs" etc. are descriptive suffixes present in
# thousands of company names, so matching solely on them produces false
# positives like "X Ventures" → "MarketX Ventures".
_BUSINESS_STOPWORDS = frozenset({
    "ventures", "capital", "labs", "group", "finance", "protocol",
    "network", "solutions", "technologies", "technology", "holdings",
    "foundation", "foundations", "partners", "digital", "assets",
    "global", "international", "studio", "studios", "works", "co",
    "corp", "corporation", "inc", "llc", "ltd", "limited", "gmbh",
    "sa", "ag", "plc", "nv", "bv", "the", "and", "for",
})


def _meaningful_tokens(query_lc: str) -> set[str]:
    """Extract matching tokens, dropping short words and business stopwords."""
    return {
        w for w in query_lc.split()
        if len(w) >= 3 and w not in _BUSINESS_STOPWORDS
    }


def _best_match(results: list[dict], company_name: str) -> dict | None:
    """Pick the best Grid hit for a query, strictly.

    The Grid GraphQL API uses `%term%` substring matching, which produces
    false positives when the query is a substring of an unrelated name:
      - "Atos" → "Satoshigallery" (contains "atos" at position 1)
      - "X Ventures" → "MarketX Ventures" (contains "x ventures" after
        "Market", and the only non-stopword token is "ventures")

    Matching policy (strict, no fuzzy fallback):
      1. Exact name match (case-insensitive, after trimming) — always accept.
      2. Prefix match — Grid name starts with the query OR query starts
         with the Grid name (e.g. query "Kraken" vs Grid "Kraken Exchange").
      3. Word-level 100% overlap on the meaningful tokens — after filtering
         short words AND common business-suffix stopwords like "ventures",
         "capital", "labs", ALL remaining query tokens must appear as
         distinct whitespace-separated tokens in the Grid name. If every
         meaningful token is a stopword we fall through to failure — we
         refuse to match on descriptor words alone.

    Deliberately REMOVED: the "len(results) == 1 → accept" fallback and
    any <100% token overlap rule. Both produced real false positives. We
    prefer no Grid data over wrong Grid data.
    """
    if not results:
        return None
    query_lc = company_name.lower().strip()
    if not query_lc:
        return None

    # 1. Exact case-insensitive match
    for r in results:
        if r.get("name", "").lower().strip() == query_lc:
            return r

    # 2. Prefix match (either direction, with whitespace boundary)
    for r in results:
        grid_lc = r.get("name", "").lower().strip()
        if not grid_lc:
            continue
        if grid_lc.startswith(query_lc + " ") or query_lc.startswith(grid_lc + " "):
            return r

    # 3. All meaningful query tokens must appear as distinct tokens in the Grid name
    query_tokens = _meaningful_tokens(query_lc)
    if not query_tokens:
        # Every query token was a stopword or too short — can't match strictly
        return None
    for r in results:
        grid_lc = r.get("name", "").lower().strip()
        if not grid_lc:
            continue
        grid_tokens = set(grid_lc.split())
        if query_tokens.issubset(grid_tokens):
            return r

    # No strict match — refuse rather than guess
    return None


def _extract_socials(socials: list[dict]) -> dict[str, str]:
    out = {}
    for s in socials:
        slug = s.get("socialType", {}).get("slug", "")
        urls = s.get("urls") or []
        if slug and urls:
            out[slug] = urls[0].get("url", "")
    return out


def _extract_urls(urls: list[dict]) -> dict[str, str]:
    out = {}
    for u in urls:
        slug = u.get("urlType", {}).get("slug", "")
        if slug:
            out[slug] = u.get("url", "")
    return out


def _extract_media(media: list[dict]) -> dict[str, str]:
    """Extract media URLs keyed by type slug (logo_dark_bg, logo_light_bg, icon, header)."""
    out = {}
    for m in media:
        slug = m.get("mediaType", {}).get("slug", "")
        if slug and m.get("url"):
            out[slug] = m["url"]
    return out


def _build_products(products: list[dict]) -> list[dict]:
    return [
        {
            "name": p.get("name"),
            "description": p.get("description"),
            "type": (p.get("productType") or {}).get("name"),
            "type_slug": (p.get("productType") or {}).get("slug"),
            "is_main": bool(p.get("isMainProduct")),
        }
        for p in products
    ]


def _build_entities(entities: list[dict]) -> list[dict]:
    return [
        {
            "name": e.get("name"),
            "trade_name": e.get("tradeName") or None,
            "type": (e.get("entityType") or {}).get("name"),
            "country": (e.get("country") or {}).get("name"),
            "incorporated": e.get("dateOfIncorporation"),
        }
        for e in entities
    ]


def _build_grid_data(profile: dict, products: list[dict], entities: list[dict]) -> dict:
    socials = _extract_socials(profile.get("socials") or [])
    urls = _extract_urls(profile.get("urls") or [])
    media = _extract_media(profile.get("media") or [])
    sector = profile.get("profileSector") or {}

    # Pick best logo — prefer dark bg (our UI is dark), fall back to icon
    logo_url = media.get("logo_dark_bg") or media.get("icon") or media.get("logo_light_bg")

    return {
        "grid_id": profile.get("id"),
        "grid_root_id": profile.get("rootId"),
        "grid_name": profile.get("name"),
        "grid_tagline": profile.get("tagLine"),
        "grid_description": profile.get("descriptionShort"),
        "grid_description_long": profile.get("descriptionLong"),
        "grid_type": (profile.get("profileType") or {}).get("name"),
        "grid_type_slug": (profile.get("profileType") or {}).get("slug"),
        "grid_sector": sector.get("name"),
        "grid_sector_slug": sector.get("slug"),
        "grid_founded": profile.get("foundingDate"),
        "grid_logo_url": logo_url,
        "grid_media": media,
        "grid_website": urls.get("main"),
        "grid_socials": socials,
        "grid_urls": urls,
        "grid_products": _build_products(products),
        "grid_entities": _build_entities(entities),
        "grid_profile_url": f"https://thegrid.id/profiles/{profile.get('name', '').lower().replace(' ', '_')}",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


import re as _re


def _normalize_company_name(name: str) -> list[str]:
    """
    Generate search variants for domain-derived and concatenated company names.

    Examples:
      "Dragonflydigitalassets" → ["Dragonflydigitalassets", "Dragonfly Digital Assets", "Dragonfly"]
      "Proofoftalk"           → ["Proofoftalk", "Proof Of Talk", "Proof"]
      "CardanoFoundation"     → ["CardanoFoundation", "Cardano Foundation", "Cardano"]
      "clearstreet"           → ["clearstreet", "Clear Street", "Clear"]
    """
    clean = name.strip()
    if not clean:
        return []
    variants = [clean]

    # 1. Split camelCase: "CardanoFoundation" → "Cardano Foundation"
    spaced = _re.sub(r"([a-z])([A-Z])", r"\1 \2", clean)
    if spaced != clean:
        variants.append(spaced)

    # 2. Known compound suffixes — split before them (case-insensitive)
    lower = clean.lower()
    _SUFFIXES = (
        "foundation", "digital", "labs", "protocol", "network", "finance",
        "capital", "ventures", "assets", "global", "exchange", "laboratory",
        "technology", "technologies", "solutions", "group", "holdings",
        "wealth", "aligned", "ratings", "studio", "bar", "bit",
    )
    for suffix in _SUFFIXES:
        if lower.endswith(suffix) and len(lower) > len(suffix) + 2:
            prefix = clean[:len(clean) - len(suffix)]
            suffix_part = clean[len(prefix):]
            spaced_suffix = f"{prefix} {suffix_part}"
            if spaced_suffix not in variants:
                variants.append(spaced_suffix)
            if prefix.strip() not in variants and len(prefix.strip()) > 2:
                variants.append(prefix.strip())

    # 3. Known connecting words — split "proofoftalk" → "proof of talk"
    # Try ALL positions of each connector to find best split (not just first)
    _CONNECTORS = ("of", "and", "the", "for")
    for conn in _CONNECTORS:
        start = 0
        while True:
            idx = lower.find(conn, start)
            if idx < 0:
                break
            start = idx + 1
            # Both halves must be ≥ 4 chars to avoid false splits like "pro|of|talk"
            before = clean[:idx]
            after = clean[idx + len(conn):]
            if len(before.strip()) >= 4 and len(after.strip()) >= 3:
                spaced_conn = f"{before} {conn} {after}"
                if spaced_conn not in variants:
                    variants.append(spaced_conn)
                no_conn = f"{before} {after}"
                if no_conn not in variants:
                    variants.append(no_conn)

    # 4. Strip common domain-like suffixes that aren't real company names
    for strip_suffix in ("io", "ai", "co", "xyz", "fi", "me"):
        if lower.endswith(strip_suffix) and len(lower) > len(strip_suffix) + 3:
            stripped = clean[:len(clean) - len(strip_suffix)].rstrip(".")
            if stripped and stripped not in variants and len(stripped) > 2:
                variants.append(stripped)

    return variants


def _domain_to_search_term(website: str) -> str | None:
    """Extract a search-friendly name from a company website domain."""
    if not website:
        return None
    # Strip protocol and www
    domain = website.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    # Get the main part (before TLD)
    parts = domain.split(".")
    if len(parts) >= 2:
        name = parts[0]
        if name and len(name) > 2 and name not in ("com", "org", "net", "io", "ai", "co", "de"):
            return name.title()
    return None


async def _search_grid(client: httpx.AsyncClient, search_term: str) -> list[dict]:
    """
    Run Grid search with retry + case-insensitive workaround.

    _like is case-sensitive, so we try multiple case variants:
    original → Title Case → UPPER → lower. First non-empty result wins.
    Retries on transient failures (timeout, 5xx).
    """
    case_variants = list(dict.fromkeys([
        search_term,
        search_term.title(),
        search_term.upper(),
        search_term.lower(),
    ]))

    for variant in case_variants:
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    GRID_GRAPHQL_URL,
                    json={"query": PROFILE_QUERY, "variables": {"name": f"%{variant}%"}},
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code >= 500:
                    logger.warning(
                        "grid_enrichment: %d from Grid API (attempt %d, term='%s')",
                        resp.status_code, attempt + 1, variant,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_BACKOFF[attempt])
                        continue
                    return []

                resp.raise_for_status()
                data = resp.json()

                if data.get("errors"):
                    err_msg = data["errors"][0].get("message", "unknown")
                    logger.error(
                        "grid_enrichment: GraphQL error for '%s': %s", variant, err_msg,
                    )
                    # Schema-level error — don't retry, won't help
                    return []

                results = (data.get("data") or {}).get("profileInfos") or []
                if results:
                    return results
                # Empty result — try next case variant
                break

            except httpx.TimeoutException:
                logger.warning(
                    "grid_enrichment: timeout (attempt %d, term='%s')", attempt + 1, variant,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                    continue
                return []
            except httpx.HTTPError as exc:
                logger.warning("grid_enrichment: HTTP error for '%s': %s", variant, exc)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF[attempt])
                    continue
                return []

    return []


async def enrich_from_grid(company_name: str, company_website: str | None = None) -> dict | None:
    """
    Search The Grid for a company by name and return full org data:
    profile info, media/logos, products, and legal entities.

    Tries multiple search strategies:
    1. Exact company name
    2. Normalized variants (split concatenated words, strip suffixes)
    3. Domain-based search from company_website

    Returns None if no match found or API is unreachable.
    """
    if not company_name or len(company_name.strip()) < 4:
        return None

    # Build search variants
    search_variants = _normalize_company_name(company_name)

    # Add domain-based variant as fallback
    domain_name = _domain_to_search_term(company_website)
    if domain_name and domain_name.lower() != company_name.lower().strip():
        search_variants.append(domain_name)

    # Deduplicate while preserving order
    seen = set()
    unique_variants = []
    for v in search_variants:
        vl = v.lower()
        if vl not in seen:
            seen.add(vl)
            unique_variants.append(v)

    try:
        profile = None
        async with httpx.AsyncClient(timeout=20) as client:
            # Try each variant until we get a match
            for variant in unique_variants:
                results = await _search_grid(client, variant)
                profile = _best_match(results, company_name)
                if profile:
                    logger.info("grid_enrichment: matched '%s' via search '%s'", company_name, variant)
                    break
        if not profile:
            logger.info("grid_enrichment: no match for '%s'", company_name)
            return None

        # Stage 2: Fetch products + entities via rootId
        products, entities = [], []
        root_id = profile.get("rootId")
        if root_id:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp2 = await client.post(
                        GRID_GRAPHQL_URL,
                        json={"query": DETAILS_QUERY, "variables": {"rootId": root_id}},
                        headers={"Content-Type": "application/json"},
                    )
                    resp2.raise_for_status()
                    details = resp2.json()
                    d = details.get("data") or {}
                    products = d.get("products") or []
                    entities = d.get("entities") or []
            except Exception as exc:
                logger.warning("grid_enrichment: details query failed for '%s': %s", company_name, exc)

        grid_data = _build_grid_data(profile, products, entities)
        logger.info(
            "grid_enrichment: matched '%s' → '%s' (id=%s, %d products, %d entities)",
            company_name, grid_data["grid_name"], grid_data["grid_id"],
            len(products), len(entities),
        )
        return grid_data

    except httpx.HTTPError as exc:
        logger.warning("grid_enrichment: HTTP error for '%s': %s", company_name, exc)
        return None
    except Exception as exc:
        logger.error("grid_enrichment: unexpected error for '%s': %s", company_name, exc)
        return None
