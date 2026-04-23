"""
Batch enrichment + embedding script (standalone — no FastAPI server required)
==============================================================================
Fetches all attendees from Supabase, runs multi-source enrichment,
generates AI summary / intent tags / embeddings via OpenAI, and patches
the results back to Supabase.

Layers run in order:
  0. LinkedIn profile scraping (needs LINKEDIN_EMAIL + LINKEDIN_PASSWORD)
  1. Company website scraping  (no API key needed)
  2. AI summary via GPT-4o     (needs OPENAI_API_KEY)
  3. Intent classification      (needs OPENAI_API_KEY)
  4. Embedding generation       (needs OPENAI_API_KEY)

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/enrich_and_embed.py

    # Dry-run (print what would be updated, no writes):
    python scripts/enrich_and_embed.py --dry-run

    # Re-process even already-enriched attendees:
    python scripts/enrich_and_embed.py --force

    # Only scrape websites, skip AI/embedding (faster, no OpenAI cost):
    python scripts/enrich_and_embed.py --scrape-only

    # Skip LinkedIn enrichment:
    python scripts/enrich_and_embed.py --skip-linkedin
"""

import argparse
import json
import os
import sys
import asyncio
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env")
    sys.exit(1)


# ── Supabase helpers ──────────────────────────────────────────────────────────

def sb_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_all_attendees() -> list[dict]:
    """Fetch all attendees from Supabase, paginating if needed."""
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    headers = {**sb_headers(), "Prefer": "count=exact"}
    attendees = []
    offset = 0
    page_size = 100

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                url,
                headers=headers,
                params={
                    "select": "id,name,email,company,title,ticket_type,goals,interests,"
                              "linkedin_url,company_website,enriched_profile,ai_summary,intent_tags,embedding",
                    "offset": offset,
                    "limit": page_size,
                    "order": "created_at.asc",
                },
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            attendees.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

    return attendees


def patch_attendee(attendee_id: str, payload: dict, dry_run: bool) -> bool:
    """PATCH an attendee record in Supabase. Returns True on success."""
    if dry_run:
        return True
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.patch(
            url,
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{attendee_id}"},
            content=json.dumps(payload),
        )
        return resp.status_code in (200, 204)


# ── Layer 0: LinkedIn enrichment ──────────────────────────────────────────────

_linkedin_client = None
_linkedin_client_failed = False


def _get_linkedin_client():
    """Get or create the linkedin-api client (singleton)."""
    global _linkedin_client, _linkedin_client_failed
    if _linkedin_client is not None:
        return _linkedin_client
    if _linkedin_client_failed:
        return None
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        return None
    try:
        from linkedin_api import Linkedin
        _linkedin_client = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
        print(f"  LinkedIn API authenticated as {LINKEDIN_EMAIL}")
        return _linkedin_client
    except Exception as e:
        _linkedin_client_failed = True
        print(f"  LinkedIn API auth failed: {e}")
        return None


import re


def fetch_linkedin_profile(linkedin_url: str) -> dict | None:
    """Fetch LinkedIn profile data using linkedin-api's session + dash endpoint.

    The library's get_profile() uses the old 410'd endpoint, so we use the
    library only for auth and call the working dash/profiles endpoint directly.
    """
    client = _get_linkedin_client()
    if not client:
        return None
    try:
        match = re.search(r"/in/([^/?#]+)", linkedin_url)
        if not match:
            return None
        profile_id = match.group(1).rstrip("/")

        # Extract session cookies from linkedin-api's authenticated session
        cookies = client.client.session.cookies
        li_at = cookies.get("li_at", domain=".linkedin.com") or cookies.get("li_at")
        csrf = cookies.get("JSESSIONID", domain=".linkedin.com") or cookies.get("JSESSIONID")
        if not li_at:
            print(f"    No li_at cookie in linkedin-api session")
            return None
        csrf_clean = csrf.strip('"') if csrf else ""

        headers = {
            "Cookie": f'li_at={li_at}; JSESSIONID="{csrf_clean}"',
            "csrf-token": csrf_clean,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "x-restli-protocol-version": "2.0.0",
            "x-li-lang": "en_US",
        }

        resp = httpx.get(
            "https://www.linkedin.com/voyager/api/identity/dash/profiles",
            params={
                "q": "memberIdentity",
                "memberIdentity": profile_id,
                "decorationId": "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-86",
            },
            headers=headers,
            follow_redirects=True,
            timeout=15,
        )
        if resp.status_code not in (200, 403):
            print(f"    LinkedIn API {resp.status_code} for {profile_id}")
            return None

        data = resp.json()
        included = data.get("included", [])
        if not included:
            return {"headline": None, "summary": None, "experiences": [], "skills": [],
                    "education": [], "source": "linkedin_api_private"}

        # Parse dash response
        profile_obj = next(
            (i for i in included if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Profile"), {}
        )
        positions = [i for i in included if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Position"]
        skills_list = [i for i in included if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Skill"]
        educations = [i for i in included if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Education"]

        experiences = [
            {"title": pos.get("title"), "company": pos.get("companyName"), "description": pos.get("description")}
            for pos in positions[:5]
        ]
        skills = [s.get("name") for s in skills_list[:15] if s.get("name")]
        education = [
            {"school": edu.get("schoolName"), "degree": edu.get("degreeName"), "field": edu.get("fieldOfStudy")}
            for edu in educations[:3]
        ]

        # Extract photo URL
        profile_pic_url = None
        try:
            vector_image = (
                profile_obj.get("profilePicture", {})
                .get("displayImageReference", {})
                .get("vectorImage", {})
            )
            root_url = vector_image.get("rootUrl", "")
            artifacts = vector_image.get("artifacts", [])
            if root_url and artifacts:
                largest = max(artifacts, key=lambda a: a.get("width", 0))
                profile_pic_url = root_url + largest.get("fileIdentifyingUrlPathSegment", "")
        except Exception:
            pass

        return {
            "headline": profile_obj.get("headline"),
            "summary": profile_obj.get("summary"),
            "profile_pic_url": profile_pic_url,
            "experiences": experiences,
            "skills": skills,
            "education": education,
            "industry": profile_obj.get("industryName"),
            "location": profile_obj.get("geoLocationName"),
            "source": "linkedin_api",
        }
    except Exception as e:
        print(f"    LinkedIn error for {linkedin_url}: {e}")
        return None


def summarize_linkedin(data: dict) -> str:
    """Create a text summary from LinkedIn data."""
    parts = []
    if data.get("headline"):
        parts.append(data["headline"])
    if data.get("summary"):
        parts.append(data["summary"][:300])
    if data.get("experiences"):
        recent = data["experiences"][0]
        parts.append(f"Current: {recent.get('title', '')} at {recent.get('company', '')}")
    if data.get("skills"):
        parts.append(f"Skills: {', '.join(data['skills'][:8])}")
    return ". ".join(parts)


# ── Layer 1: Website scraping ─────────────────────────────────────────────────

async def scrape_website(url: str) -> dict | None:
    """Scrape a company website and extract description + title."""
    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": "POTMatchmaker/1.0 (enrichment bot)"},
        follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Meta description (usually the best single-sentence summary)
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            og_tag = soup.find("meta", attrs={"property": "og:description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "").strip()
            elif og_tag:
                meta_desc = og_tag.get("content", "").strip()

            page_title = soup.title.string.strip() if soup.title else ""

            # Main body text (stripped of nav/footer/scripts)
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            body_text = soup.get_text(separator=" ", strip=True)[:2500]

            description = meta_desc or body_text[:300]
            return {
                "title": page_title,
                "description": description,
                "full_text": body_text,
            }
        except Exception as e:
            return None


# ── Layer 2–4: OpenAI (AI summary, intent tags, embedding) ────────────────────

async def call_openai_chat(messages: list[dict], max_tokens: int = 300, temperature: float = 0.3) -> str:
    """Call OpenAI chat completions API."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": OPENAI_CHAT_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


async def generate_ai_summary(attendee: dict) -> str:
    """Generate a 2-3 sentence professional profile summary.

    For sparse profiles (no interests, no goals, no meaningful enrichment),
    returns a factual stub without calling GPT.
    """
    enriched = attendee.get("enriched_profile") or {}
    company_desc = enriched.get("company_description", "")
    ticket_type = attendee.get("ticket_type", "delegate")
    title = attendee.get("title", "") or ""
    interests_raw = attendee.get("interests") or []
    goals = (attendee.get("goals") or "").strip()
    name = attendee.get("name", "")
    company = attendee.get("company", "")

    # Check for meaningful enrichment (not just Extasy ticket metadata)
    useful_keys = {"linkedin", "grid", "twitter", "crunchbase", "company_description"}
    has_enrichment = any(k in enriched for k in useful_keys)
    has_interests = len(interests_raw) > 0
    has_goals = bool(goals)

    if not has_interests and not has_goals and not has_enrichment:
        role_part = f"{title} at " if title.strip() else f"a {ticket_type} attendee from "
        return f"{name} is {role_part}{company}, attending Proof of Talk 2026 as a {ticket_type}. Specific interests and goals have not been provided."

    interests = ", ".join(interests_raw) if interests_raw else "Not specified"

    prompt = f"""You are an AI assistant for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace (2,500 decision-makers, $18T AUM).

Generate a concise 2-3 sentence professional summary for this attendee.

CRITICAL ACCURACY RULES:
- ONLY state facts directly supported by the data below.
- If Goals or Interests say "Not specified", write "Specific interests/goals have not been disclosed" — do NOT guess.
- Do NOT invent investment theses, mandates, or product descriptions not in the data.
- Do NOT claim someone "is actively seeking" unless their Goals or Interests explicitly say so.
- If Company looks like an email domain (Gmail, Googlemail, Hotmail), note company is not confirmed.
- Be specific where data exists, brief where it doesn't.

Name: {name}
Title: {title or 'Not provided'}
Company: {company or 'Unknown company'}
Ticket Type: {ticket_type}
Goals: {goals or 'Not specified'}
Interests: {interests}
Company Description: {company_desc or 'Not available'}

Write in third person."""

    return await call_openai_chat(
        [{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )


async def classify_intents(attendee: dict) -> list[str]:
    """Classify attendee intents into structured tags."""
    enriched = attendee.get("enriched_profile") or {}
    interests_raw = attendee.get("interests") or []

    prompt = f"""Classify this conference attendee's intents into structured tags.

Attendee: {attendee.get('name', '')}, {attendee.get('title', '') or 'Unknown role'} at {attendee.get('company', '') or 'Unknown company'}
Ticket: {attendee.get('ticket_type', 'delegate')}
Goals: {attendee.get('goals') or 'Not specified'}
Interests: {', '.join(interests_raw) if interests_raw else 'Not specified'}
Company: {enriched.get('company_description', 'Not available')}

Return ONLY a JSON array of 2-4 intent tags from:
["deploying_capital", "raising_capital", "seeking_partnerships", "seeking_customers",
 "regulatory_engagement", "technology_evaluation", "deal_making", "knowledge_exchange",
 "co_investment", "talent_acquisition"]

Nothing else."""

    raw = await call_openai_chat(
        [{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.1,
    )
    # Strip markdown if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        tags = json.loads(raw)
        return tags if isinstance(tags, list) else ["knowledge_exchange"]
    except json.JSONDecodeError:
        return ["knowledge_exchange"]


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding via OpenAI text-embedding-3-small."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": OPENAI_EMBEDDING_MODEL, "input": text},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


def build_composite_text(attendee: dict) -> str:
    """Build the composite text blob used for embedding."""
    enriched = attendee.get("enriched_profile") or {}
    interests_raw = attendee.get("interests") or []
    parts = [
        f"Name: {attendee.get('name', '')}",
        f"Title: {attendee.get('title', '') or 'Unknown role'}",
        f"Company: {attendee.get('company', '') or 'Unknown company'}",
        f"Ticket Type: {attendee.get('ticket_type', 'delegate')}",
    ]
    if interests_raw:
        parts.append(f"Interests: {', '.join(interests_raw)}")
    if attendee.get("goals"):
        parts.append(f"Goals: {attendee['goals']}")
    if attendee.get("ai_summary"):
        parts.append(f"Profile Summary: {attendee['ai_summary']}")
    if enriched.get("linkedin_summary"):
        parts.append(f"LinkedIn: {enriched['linkedin_summary']}")
    if enriched.get("company_description"):
        parts.append(f"Company Info: {enriched['company_description']}")
    if enriched.get("recent_activity"):
        parts.append(f"Recent Activity: {enriched['recent_activity']}")
    return "\n".join(parts)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def process_attendee(
    attendee: dict,
    dry_run: bool,
    force: bool,
    scrape_only: bool,
    skip_linkedin: bool = False,
) -> str:
    """Run enrichment + AI pipeline for a single attendee. Returns status string."""
    name = attendee.get("name", "Unknown")
    aid = attendee["id"]
    enriched = dict(attendee.get("enriched_profile") or {})

    patch = {}
    status_parts = []

    # ── Layer 0: LinkedIn enrichment ──────────────────────────────────────────
    already_has_linkedin = bool(enriched.get("linkedin"))
    linkedin_url = attendee.get("linkedin_url", "")

    if not skip_linkedin and linkedin_url and (force or not already_has_linkedin):
        linkedin_data = fetch_linkedin_profile(linkedin_url)
        if linkedin_data:
            enriched["linkedin"] = linkedin_data
            enriched["linkedin_summary"] = summarize_linkedin(linkedin_data)
            enriched["linkedin_enriched_at"] = __import__("datetime").datetime.utcnow().isoformat()
            # Auto-populate title/company from LinkedIn if missing in registration
            if not attendee.get("title") and linkedin_data.get("headline"):
                patch["title"] = linkedin_data["headline"]
            status_parts.append("linkedin✓")
            # Rate limit: 3s between LinkedIn requests
            await asyncio.sleep(3)
        else:
            status_parts.append("linkedin✗")
    elif already_has_linkedin and not force:
        status_parts.append("linkedin=cached")
    elif not linkedin_url:
        status_parts.append("linkedin=no_url")
    else:
        status_parts.append("linkedin=skipped")

    # ── Layer 1: Website scraping ──────────────────────────────────────────────
    already_scraped = bool(enriched.get("company_description"))
    website_url = attendee.get("company_website", "")

    if website_url and (force or not already_scraped):
        website_data = await scrape_website(website_url)
        if website_data:
            enriched["website"] = website_data
            enriched["company_description"] = website_data.get("description", "")
            enriched["website_enriched_at"] = __import__("datetime").datetime.utcnow().isoformat()
            status_parts.append("website✓")
        else:
            status_parts.append("website✗")
    elif already_scraped and not force:
        status_parts.append("website=cached")
    else:
        status_parts.append("website=no_url")

    if enriched != (attendee.get("enriched_profile") or {}):
        patch["enriched_profile"] = enriched

    if scrape_only:
        # Only persist website data, skip AI/embedding
        if patch and not dry_run:
            ok = patch_attendee(aid, patch, dry_run=False)
            return f"{'DRY ' if dry_run else ''}{name}: {', '.join(status_parts)} | patch={'ok' if ok else 'ERR'}"
        return f"{'DRY ' if dry_run else ''}{name}: {', '.join(status_parts)}"

    # ── Layer 2: AI Summary ────────────────────────────────────────────────────
    if not OPENAI_API_KEY:
        return f"{name}: SKIP (no OPENAI_API_KEY)"

    already_has_summary = bool(attendee.get("ai_summary"))
    if force or not already_has_summary:
        # Use updated enriched_profile for summary generation
        attendee_for_ai = {**attendee, "enriched_profile": enriched}
        summary = await generate_ai_summary(attendee_for_ai)
        patch["ai_summary"] = summary
        status_parts.append("summary✓")
    else:
        summary = attendee["ai_summary"]
        status_parts.append("summary=cached")

    # ── Layer 3: Intent tags ───────────────────────────────────────────────────
    already_has_tags = bool(attendee.get("intent_tags"))
    if force or not already_has_tags:
        attendee_for_ai = {**attendee, "enriched_profile": enriched}
        tags = await classify_intents(attendee_for_ai)
        patch["intent_tags"] = tags
        # Compute deal_readiness_score
        deal_signals = {"deploying_capital", "raising_capital", "deal_making", "seeking_customers"}
        patch["deal_readiness_score"] = len(set(tags) & deal_signals) / len(deal_signals)
        status_parts.append("tags✓")
    else:
        status_parts.append("tags=cached")

    # ── Layer 4: Embedding ─────────────────────────────────────────────────────
    already_has_embedding = bool(attendee.get("embedding"))
    if force or not already_has_embedding:
        # Build composite text with updated summary
        attendee_for_embed = {**attendee, "enriched_profile": enriched, "ai_summary": patch.get("ai_summary", attendee.get("ai_summary"))}
        composite = build_composite_text(attendee_for_embed)
        embedding = await generate_embedding(composite)
        # pgvector expects a string like "[0.1, 0.2, ...]"
        patch["embedding"] = "[" + ",".join(str(v) for v in embedding) + "]"
        status_parts.append("embed✓")
    else:
        status_parts.append("embed=cached")

    patch["enriched_at"] = __import__("datetime").datetime.utcnow().isoformat()

    # ── Persist ────────────────────────────────────────────────────────────────
    if dry_run:
        return f"DRY {name}: {', '.join(status_parts)}"

    ok = patch_attendee(aid, patch, dry_run=False)
    return f"{name}: {', '.join(status_parts)} | patch={'ok' if ok else 'ERR'}"


async def run(dry_run: bool, force: bool, scrape_only: bool, skip_linkedin: bool = False) -> None:
    print("=== POT Matchmaker — Batch Enrichment + Embedding ===\n")

    if not OPENAI_API_KEY and not scrape_only:
        print("WARNING: OPENAI_API_KEY not set — will run website scraping only.\n")
        scrape_only = True

    # LinkedIn availability check
    if not skip_linkedin and (LINKEDIN_EMAIL and LINKEDIN_PASSWORD):
        print("LinkedIn enrichment: ENABLED (linkedin-api)\n")
    elif skip_linkedin:
        print("LinkedIn enrichment: SKIPPED (--skip-linkedin)\n")
    else:
        print("LinkedIn enrichment: DISABLED (set LINKEDIN_EMAIL + LINKEDIN_PASSWORD in .env)\n")
        skip_linkedin = True

    print("Fetching attendees from Supabase...")
    attendees = fetch_all_attendees()
    print(f"  Found {len(attendees)} attendees\n")

    if not attendees:
        print("No attendees found. Run ingest_extasy.py first.")
        return

    # Summary of enrichment state
    needs_linkedin = sum(
        1 for a in attendees
        if a.get("linkedin_url") and not (a.get("enriched_profile") or {}).get("linkedin")
    )
    needs_scraping = sum(
        1 for a in attendees
        if not (a.get("enriched_profile") or {}).get("company_description")
    )
    needs_ai = sum(1 for a in attendees if not a.get("ai_summary"))
    needs_embedding = sum(1 for a in attendees if not a.get("embedding"))

    print(f"  Needs LinkedIn:         {needs_linkedin}")
    print(f"  Needs website scraping: {needs_scraping}")
    print(f"  Needs AI summary:       {needs_ai}")
    print(f"  Needs embedding:        {needs_embedding}")
    print()

    if not force and needs_linkedin == 0 and needs_scraping == 0 and needs_ai == 0 and needs_embedding == 0:
        print("All attendees already enriched. Use --force to re-process.")
        return

    print(f"{'DRY RUN — ' if dry_run else ''}Processing {len(attendees)} attendees...\n")

    ok_count = 0
    err_count = 0

    for attendee in attendees:
        result = await process_attendee(attendee, dry_run=dry_run, force=force, scrape_only=scrape_only, skip_linkedin=skip_linkedin)
        has_error = "ERR" in result
        status_char = "✗" if has_error else "✓"
        print(f"  {status_char} {result}")
        if has_error:
            err_count += 1
        else:
            ok_count += 1

    print(f"\n{'DRY RUN ' if dry_run else ''}Done: {ok_count} ok, {err_count} errors / {len(attendees)} total")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch enrich and embed all attendees")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be updated without writing")
    parser.add_argument("--force", action="store_true", help="Re-process even already-enriched attendees")
    parser.add_argument("--scrape-only", action="store_true", help="Only run website scraping, skip AI/embedding")
    parser.add_argument("--skip-linkedin", action="store_true", help="Skip LinkedIn enrichment")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, force=args.force, scrape_only=args.scrape_only, skip_linkedin=args.skip_linkedin))
