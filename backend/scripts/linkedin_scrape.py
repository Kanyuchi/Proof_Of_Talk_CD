"""
LinkedIn profile scraper using Playwright + real Chrome session.
================================================================
Opens LinkedIn profiles in a real browser context (using your Chrome
cookies), extracts visible profile data from the rendered page, and
patches it into Supabase.

This is NOT an API call — it renders the actual page like a human
visiting it. Rate-limited to 5 seconds between profiles.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/linkedin_scrape.py              # scrape all with linkedin_url
    python scripts/linkedin_scrape.py --dry-run    # preview without writing
    python scripts/linkedin_scrape.py --limit 5    # first 5 only
    python scripts/linkedin_scrape.py --discover   # also try to find URLs for those without
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DELAY_SECONDS = 10  # seconds between profile visits

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    sys.exit(1)


# ── Supabase helpers ──────────────────────────────────────────────────────

import httpx

def sb_headers():
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_attendees(with_url_only: bool = True) -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    params = {
        "select": "id,name,email,company,title,linkedin_url,enriched_profile",
        "order": "created_at.asc",
        "limit": "500",
    }
    if with_url_only:
        params["linkedin_url"] = "not.is.null"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=sb_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


def patch_attendee(aid: str, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.patch(
            url,
            headers={**sb_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{aid}"},
            content=json.dumps(payload),
        )
        return resp.status_code in (200, 204)


# ── Playwright scraper ────────────────────────────────────────────────────

async def scrape_linkedin_profile(page, linkedin_url: str) -> dict | None:
    """Navigate to a LinkedIn profile and extract visible data."""
    try:
        await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)  # let dynamic content load

        # Check if we're redirected to login
        if "/login" in page.url or "/authwall" in page.url:
            print(f"    Redirected to: {page.url}")
            return None

        # Scroll down to trigger lazy loading of experience/about/skills
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(500)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        data = await page.evaluate("""() => {
            // Get page title for name (most reliable)
            const titleMatch = document.title.match(/^(.+?)\\s*[|\\-–]\\s*LinkedIn/);
            const name = titleMatch ? titleMatch[1].trim() : null;

            // Find headline — it's usually the first <p> after the name
            // that contains job-related keywords like "|" or "at" or common titles
            let headline = null;
            const allPs = [...document.querySelectorAll('p')];
            for (const p of allPs) {
                const text = p.innerText.trim();
                if (text.length > 15 && text.length < 300 &&
                    (text.includes('|') || text.includes(' at ') ||
                     /\\b(CEO|CTO|CIO|COO|CFO|VP|Director|Head|Manager|Engineer|Founder|Partner|Investor|Analyst|Advisor|Consultant)\\b/i.test(text))) {
                    headline = text;
                    break;
                }
            }

            // About section — look for long paragraph text
            let summary = null;
            for (const p of allPs) {
                const text = p.innerText.trim();
                if (text.length > 100 && text.length < 3000 &&
                    !text.includes('LinkedIn') && !text.includes('cookie') &&
                    !text.includes('notifications')) {
                    summary = text;
                    break;
                }
            }

            // Experience — find sections with job titles
            const experiences = [];
            const allSections = [...document.querySelectorAll('section')];
            for (const section of allSections) {
                const heading = section.querySelector('h2');
                if (heading && /experience/i.test(heading.innerText)) {
                    const items = section.querySelectorAll('li');
                    for (const item of [...items].slice(0, 5)) {
                        const texts = [...item.querySelectorAll('span, p')]
                            .map(el => el.innerText.trim())
                            .filter(t => t.length > 2 && t.length < 100);
                        if (texts.length >= 1) {
                            experiences.push({
                                title: texts[0],
                                company: texts[1] || null,
                            });
                        }
                    }
                    break;
                }
            }

            // Profile photo — any img with the person's name in alt text
            let photoUrl = null;
            if (name) {
                const firstName = name.split(' ')[0];
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {
                    const alt = img.alt || '';
                    if (alt.includes(firstName) && img.src && img.src.startsWith('http') && img.width > 50) {
                        photoUrl = img.src;
                        break;
                    }
                }
            }

            return { name, headline, summary, experiences, skills: [], education: [], photoUrl };
        }""")

        # Validate we got something useful
        if not data or not data.get("headline"):
            return None

        # Return with scraped name for validation
        data["scraped_name"] = data.get("name")

        return {
            "headline": data.get("headline"),
            "summary": data.get("summary"),
            "experiences": data.get("experiences", []),
            "skills": data.get("skills", []),
            "education": data.get("education", []),
            "profile_pic_url": data.get("photoUrl"),
            "source": "playwright_scrape",
        }

    except Exception as e:
        print(f"    Error scraping: {e}")
        return None


async def discover_linkedin_url(page, name: str, company: str) -> str | None:
    """Find a LinkedIn profile by searching name + company on LinkedIn search."""
    parts = name.lower().split()
    if len(parts) < 2:
        return None

    # Build search query: "firstname lastname company"
    query = f"{name} {company}".strip() if company else name
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={query.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER"

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3000)

        # Check we're not on login/authwall
        if "/login" in page.url or "/authwall" in page.url:
            return None

        # Find the first search result link that points to a profile
        result = await page.evaluate("""(searchName) => {
            const parts = searchName.toLowerCase().split(/\\s+/);
            const firstName = parts[0];
            const lastName = parts[parts.length - 1];

            // Find all result links to /in/ profiles
            const links = [...document.querySelectorAll('a[href*="/in/"]')];
            for (const link of links) {
                const href = link.getAttribute('href') || '';
                if (!href.includes('/in/') || href.includes('/search/')) continue;

                // Check if the link text or nearby text contains the person's name
                const container = link.closest('li') || link.closest('div') || link;
                const text = container.innerText.toLowerCase();

                if (text.includes(firstName) && text.includes(lastName)) {
                    // Extract clean profile URL
                    const match = href.match(/\\/in\\/([^/?]+)/);
                    if (match) {
                        return 'https://www.linkedin.com/in/' + match[1];
                    }
                }
            }
            return null;
        }""", name)

        return result

    except Exception as e:
        print(f"    Discovery error: {e}")
        return None


async def run(dry_run: bool, limit: int | None, discover: bool):
    print("=== LinkedIn Profile Scraper (Playwright) ===\n")

    # Fetch attendees
    if discover:
        attendees = fetch_attendees(with_url_only=False)
        attendees_with_url = [a for a in attendees if a.get("linkedin_url")]
        attendees_without_url = [a for a in attendees if not a.get("linkedin_url")]
        print(f"  Attendees with LinkedIn URL: {len(attendees_with_url)}")
        print(f"  Attendees without URL (will try discovery): {len(attendees_without_url)}")
    else:
        attendees_with_url = fetch_attendees(with_url_only=True)
        attendees_without_url = []
        print(f"  Attendees with LinkedIn URL: {len(attendees_with_url)}")

    # In discover mode, process discovery candidates first, then existing URLs
    all_targets = attendees_without_url + attendees_with_url if discover else attendees_with_url + attendees_without_url
    if limit:
        all_targets = all_targets[:limit]
    print(f"  Processing: {len(all_targets)}\n")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # Navigate to LinkedIn login — user logs in manually (including 2FA)
        print("  Opening LinkedIn login page...")
        print("  ➡️  Log in manually in the browser window (including 2FA).")
        print("  ➡️  The script will wait up to 3 minutes for you to complete login.\n")
        await page.goto("https://www.linkedin.com/login", timeout=30000)

        # Wait until we land on the feed (login + 2FA complete)
        # Poll every 3 seconds for up to 3 minutes
        logged_in = False
        for attempt in range(60):
            await page.wait_for_timeout(3000)
            url = page.url
            if "/feed" in url or "/mynetwork" in url or "/messaging" in url:
                logged_in = True
                break
            if attempt % 10 == 9:
                print(f"  ⏳ Still waiting for login... ({(attempt+1)*3}s)")

        if not logged_in:
            print("  ❌ Login timed out after 3 minutes. Please try again.")
            await browser.close()
            return
        print("  ✅ Logged in\n")

        enriched_count = 0
        discovered_count = 0
        skipped_count = 0
        errors = 0

        for i, attendee in enumerate(all_targets):
            name = attendee.get("name", "Unknown")
            linkedin_url = attendee.get("linkedin_url")

            # Discovery mode for attendees without URL
            if not linkedin_url and discover:
                print(f"  [{i+1}/{len(all_targets)}] {name} — discovering URL...")
                linkedin_url = await discover_linkedin_url(
                    page, name, attendee.get("company", "")
                )
                if linkedin_url:
                    print(f"    Found: {linkedin_url}")
                    discovered_count += 1
                    if not dry_run:
                        patch_attendee(attendee["id"], {"linkedin_url": linkedin_url})
                else:
                    print(f"    Not found")
                    skipped_count += 1
                    continue
                time.sleep(DELAY_SECONDS)

            if not linkedin_url:
                skipped_count += 1
                continue

            # Clean URL
            if not linkedin_url.startswith("http"):
                linkedin_url = f"https://www.linkedin.com/in/{linkedin_url}"

            print(f"  [{i+1}/{len(all_targets)}] {name} — {linkedin_url}")

            data = await scrape_linkedin_profile(page, linkedin_url)

            if data and data.get("headline"):
                # Validate scraped name matches our attendee (reject wrong-person matches)
                scraped_name = (data.get("scraped_name") or "").lower()
                our_name_parts = name.lower().split()
                name_match = (
                    not scraped_name or  # if no name scraped, accept (we have headline)
                    any(part in scraped_name for part in our_name_parts if len(part) > 2)
                )
                if not name_match:
                    print(f"    ❌ Wrong person: scraped '{data.get('scraped_name')}', expected '{name}' — skipping")
                    skipped_count += 1
                    await asyncio.sleep(DELAY_SECONDS)
                    continue

                print(f"    ✅ {data['headline'][:60]}")
                if data.get("experiences"):
                    print(f"    📋 {len(data['experiences'])} experiences, {len(data.get('skills', []))} skills")

                if not dry_run:
                    enriched = dict(attendee.get("enriched_profile") or {})
                    enriched["linkedin"] = data
                    enriched["linkedin_enriched_at"] = __import__("datetime").datetime.utcnow().isoformat()

                    # Build summary from LinkedIn data
                    summary_parts = []
                    if data.get("headline"):
                        summary_parts.append(data["headline"])
                    if data.get("summary"):
                        summary_parts.append(data["summary"][:200])
                    enriched["linkedin_summary"] = " | ".join(summary_parts)

                    patch_payload = {"enriched_profile": enriched}

                    # Auto-fill title if empty
                    if not attendee.get("title") and data.get("experiences"):
                        patch_payload["title"] = data["experiences"][0].get("title", "")

                    # Auto-fill photo
                    if data.get("profile_pic_url"):
                        patch_payload["photo_url"] = data["profile_pic_url"]

                    ok = patch_attendee(attendee["id"], patch_payload)
                    if ok:
                        enriched_count += 1
                    else:
                        errors += 1
                        print(f"    ❌ Supabase patch failed")
                else:
                    enriched_count += 1
            else:
                print(f"    ⚠ No data extracted (private or blocked)")
                skipped_count += 1

            # Rate limit
            await asyncio.sleep(DELAY_SECONDS)

        await context.close()
        await browser.close()

    prefix = "DRY-RUN " if dry_run else ""
    print(f"\n{prefix}Done: {enriched_count} enriched, {discovered_count} URLs discovered, {skipped_count} skipped, {errors} errors / {len(all_targets)} total")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape LinkedIn profiles using Playwright")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Supabase")
    parser.add_argument("--limit", type=int, default=None, help="Max profiles to process")
    parser.add_argument("--discover", action="store_true", help="Also try to find URLs for attendees without one")
    args = parser.parse_args()

    asyncio.run(run(dry_run=args.dry_run, limit=args.limit, discover=args.discover))
