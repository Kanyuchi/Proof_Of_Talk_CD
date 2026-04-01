"""
The Grid B2B Enrichment
=======================
Queries The Grid (thegrid.id) GraphQL API for verified Web3 company data.
No authentication required — API is publicly accessible.

Fetches: profile info (logo, description, sector, socials), products, and entities.

Endpoint: https://beta.node.thegrid.id/graphql
Explorer: https://cloud.hasura.io/public/graphiql?endpoint=https://beta.node.thegrid.id/graphql
"""

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

GRID_GRAPHQL_URL = "https://beta.node.thegrid.id/graphql"

# Stage 1: Find the profile and get rootId for cross-entity queries
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


def _best_match(results: list[dict], company_name: str) -> dict | None:
    if not results:
        return None
    if len(results) == 1:
        return results[0]
    lower = company_name.lower().strip()
    for r in results:
        if r["name"].lower().strip() == lower:
            return r
    return results[0]


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


async def enrich_from_grid(company_name: str) -> dict | None:
    """
    Search The Grid for a company by name and return full org data:
    profile info, media/logos, products, and legal entities.

    Returns None if no match found or API is unreachable.
    """
    if not company_name or len(company_name.strip()) < 2:
        return None

    search_term = f"%{company_name.strip()}%"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Stage 1: Find profile
            resp = await client.post(
                GRID_GRAPHQL_URL,
                json={"query": PROFILE_QUERY, "variables": {"name": search_term}},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("errors"):
            logger.warning("grid_enrichment: GraphQL errors for '%s': %s", company_name, data["errors"])
            return None

        results = (data.get("data") or {}).get("profileInfos") or []
        profile = _best_match(results, company_name)
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
