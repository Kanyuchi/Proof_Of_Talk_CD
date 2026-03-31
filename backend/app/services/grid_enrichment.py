"""
The Grid B2B Enrichment
=======================
Queries The Grid (thegrid.id) GraphQL API for verified Web3 company data.
No authentication required — API is publicly accessible.

Endpoint: https://beta.node.thegrid.id/graphql
Explorer: https://cloud.hasura.io/public/graphiql?endpoint=https://beta.node.thegrid.id/graphql
"""

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

GRID_GRAPHQL_URL = "https://beta.node.thegrid.id/graphql"

PROFILE_QUERY = """
query SearchCompany($name: String!) {
  profileInfos(limit: 3, where: {name: {_like: $name}, profileStatus: {slug: {_eq: "active"}}}) {
    id
    name
    descriptionShort
    profileType { name slug }
    profileSector { name slug }
    foundingDate
    urls { url urlType { name slug } }
    socials { name socialType { name slug } urls { url } }
  }
}
"""


def _best_match(results: list[dict], company_name: str) -> dict | None:
    """Pick the best matching profile from Grid results."""
    if not results:
        return None
    if len(results) == 1:
        return results[0]
    # Prefer exact name match (case-insensitive)
    lower = company_name.lower().strip()
    for r in results:
        if r["name"].lower().strip() == lower:
            return r
    # Fall back to first result (Grid ranks by relevance)
    return results[0]


def _extract_socials(socials: list[dict]) -> dict[str, str]:
    """Extract social URLs keyed by platform slug."""
    out = {}
    for s in socials:
        slug = s.get("socialType", {}).get("slug", "")
        urls = s.get("urls") or []
        if slug and urls:
            out[slug] = urls[0].get("url", "")
    return out


def _extract_urls(urls: list[dict]) -> dict[str, str]:
    """Extract URLs keyed by type slug."""
    out = {}
    for u in urls:
        slug = u.get("urlType", {}).get("slug", "")
        if slug:
            out[slug] = u.get("url", "")
    return out


def _build_grid_data(profile: dict) -> dict:
    """Transform a Grid profile into our enriched_profile['grid'] format."""
    socials = _extract_socials(profile.get("socials") or [])
    urls = _extract_urls(profile.get("urls") or [])
    sector = profile.get("profileSector") or {}

    return {
        "grid_id": profile.get("id"),
        "grid_name": profile.get("name"),
        "grid_description": profile.get("descriptionShort"),
        "grid_type": (profile.get("profileType") or {}).get("name"),
        "grid_sector": sector.get("name"),
        "grid_sector_slug": sector.get("slug"),
        "grid_founded": profile.get("foundingDate"),
        "grid_website": urls.get("main"),
        "grid_socials": socials,
        "grid_urls": urls,
        "grid_profile_url": f"https://thegrid.id/profiles/{profile.get('name', '').lower().replace(' ', '_')}",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def enrich_from_grid(company_name: str) -> dict | None:
    """
    Search The Grid for a company by name and return structured B2B data.

    Returns None if no match found or API is unreachable.
    """
    if not company_name or len(company_name.strip()) < 2:
        return None

    search_term = f"%{company_name.strip()}%"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                GRID_GRAPHQL_URL,
                json={"query": PROFILE_QUERY, "variables": {"name": search_term}},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        errors = data.get("errors")
        if errors:
            logger.warning("grid_enrichment: GraphQL errors for '%s': %s", company_name, errors)
            return None

        results = (data.get("data") or {}).get("profileInfos") or []
        profile = _best_match(results, company_name)
        if not profile:
            logger.info("grid_enrichment: no match for '%s'", company_name)
            return None

        grid_data = _build_grid_data(profile)
        logger.info("grid_enrichment: matched '%s' → '%s' (id=%s)", company_name, grid_data["grid_name"], grid_data["grid_id"])
        return grid_data

    except httpx.HTTPError as exc:
        logger.warning("grid_enrichment: HTTP error for '%s': %s", company_name, exc)
        return None
    except Exception as exc:
        logger.error("grid_enrichment: unexpected error for '%s': %s", company_name, exc)
        return None
