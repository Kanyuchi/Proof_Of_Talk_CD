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


def fetch_attendees(with_url_only: bool = True, missing_photo_only: bool = False) -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    params = {
        "select": "id,name,email,company,title,linkedin_url,photo_url,enriched_profile",
        # Newest first — when scraping is rate-limited and we can only do
        # a few per session, the latest registrations (who need matches
        # right now) get priority. Older attendees who've been missing a
        # photo for weeks can wait one more day.
        "order": "created_at.desc",
        "limit": "500",
    }
    if with_url_only:
        params["linkedin_url"] = "not.is.null"
    if missing_photo_only:
        # PostgREST: photo_url is null OR empty string
        params["photo_url"] = "is.null"
    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=sb_headers(), params=params)
        resp.raise_for_status()
        rows = resp.json()
    # Skip rows we've already concluded are unscrapable (private profiles,
    # repeated 403s). Flagged manually after 4+ failed attempts. Keeps the
    # newest-first queue from wasting 5 slots on the same dead profiles
    # every batch.
    rows = [r for r in rows if not ((r.get("enriched_profile") or {}).get("linkedin_unscrapable"))]
    return rows


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

        # Wait for the profile avatar to render before reading data.
        # LinkedIn lazy-loads the top-card photo — without this wait, ~25%
        # of scrapes ended up with ✅ enriched but photo_url NULL (Josiah,
        # Luca, Nikhil's first attempt, etc). Up to 4s; if no avatar selector
        # ever matches the profile is likely photo-less and we just continue.
        try:
            await page.wait_for_selector(
                'img.pv-top-card-profile-picture__image, '
                'img[src*="profile-displayphoto"], '
                'img[src*="profile-framedphoto"], '
                'button[aria-label*="profile photo" i] img',
                state="visible",
                timeout=4000,
            )
        except Exception:
            pass

        # Click "…see more" expanders before reading text. Without this,
        # LinkedIn truncates About to ~250 chars and we capture half a
        # sentence ("…until I (my"). Try the common selectors; ignore
        # errors if no expander present.
        try:
            await page.evaluate("""() => {
                const buttons = [...document.querySelectorAll('button')];
                for (const b of buttons) {
                    const label = (b.getAttribute('aria-label') || b.innerText || '').toLowerCase();
                    if (/see more|…see more|show more/.test(label) && b.offsetParent !== null) {
                        try { b.click(); } catch (_) {}
                    }
                }
            }""")
            await page.wait_for_timeout(500)
        except Exception:
            pass

        data = await page.evaluate("""() => {
            // Get page title for name (most reliable). Strip leading
            // notification count "(7) " — when the logged-in user has
            // unread badges, LinkedIn prepends "(N) " to every page title,
            // which broke first-name extraction and silently rejected
            // every photo via the alt-text safety check (Cynthia Lo Bessette,
            // Johnna Powell, Steven Goldfeder, … — 9 cases in batch 3).
            const rawTitle = document.title.replace(/^\\s*\\(\\d+\\)\\s*/, '');
            const titleMatch = rawTitle.match(/^(.+?)\\s*[|\\-–]\\s*LinkedIn/);
            const name = titleMatch ? titleMatch[1].trim() : null;

            // Find the profile owner's <h1> (their name) — the structural
            // anchor for headline + photo extraction. Same approach used
            // below for photo. The h1 is stable across LinkedIn redesigns;
            // every profile page has exactly one h1 for the owner's name,
            // inside <main> and not in any nav/header/dialog.
            const _allH1s = [...document.querySelectorAll('h1')];
            const ownerH1 = _allH1s.find(h => {
                const inMain = h.closest('main');
                const inNav = h.closest('header, nav, [role="dialog"]');
                return inMain && !inNav;
            });

            // Find the top-card container by walking up from the h1 until
            // we hit a section/article that contains a sibling text element
            // (the headline) OR until we'd cross into <main>.
            let topCardEl = null;
            if (ownerH1) {
                let walker = ownerH1.parentElement;
                for (let i = 0; i < 6 && walker; i++) {
                    if (walker.tagName === 'MAIN' || walker.tagName === 'BODY') break;
                    if (walker.tagName === 'SECTION' || walker.tagName === 'ARTICLE') {
                        topCardEl = walker;
                        break;
                    }
                    walker = walker.parentElement;
                }
                if (!topCardEl) topCardEl = ownerH1.parentElement;
            }

            // Headline extraction with anti-post filters. The original
            // page-wide <p>-scan with " at "/"|" keyword match grabbed
            // recent feed post text for several attendees on 2026-05-18
            // (Tony McLaughlin's Money20/20 post, Maha Al-Saadi's "We
            // brought together CEOs..." post, Nicholas Pelecanos's altcoin
            // valuation post, Alexis Tasset's "Investors Club" UI fragment).
            // We keep the page-wide scan but reject anything that smells
            // like a post: 2+ hashtags, post-starter phrases, etc.
            //
            // Also try to detect headline from the top-card region first
            // (the real headline is the closest text to the owner's h1).
            const _isPostLike = (text) => {
                if ((text.match(/#\\w+/g) || []).length >= 2) return true;
                if (/^\\s*(I['’]ll|I['’]m|I have|We have|Just |Today |Yesterday |Excited |Honoured |Thrilled |Delighted |Proud )/i.test(text)) return true;
                if (/\\b(speaking at|spoke at|on stage|in the room|sponsored by|congrats|congratulations)\\b/i.test(text)) return true;
                if (/\\b(you and \\w+ are both in|you and \\w+ are connected)/i.test(text)) return true;
                return false;
            };

            let headline = null;
            // Pass 1: scan elements near the owner's h1 first (more reliable).
            if (ownerH1) {
                const ownerName = ownerH1.innerText.trim().toLowerCase();
                const scope = topCardEl || ownerH1.parentElement || document.body;
                const nearby = [...scope.querySelectorAll('div, span, p')]
                    .filter(el => (ownerH1.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING));
                for (const el of nearby.slice(0, 30)) {
                    const text = (el.innerText || '').trim();
                    if (text.length < 8 || text.length > 300) continue;
                    if (text.toLowerCase() === ownerName) continue;
                    if (_isPostLike(text)) continue;
                    if (/^(she|he|they)\\s*\\//i.test(text)) continue;
                    if (/\\d+\\s*(connections|followers|mutual)/i.test(text)) continue;
                    if (/contact info/i.test(text)) continue;
                    if (/^\\s*(message|connect|follow|more|share|save|copy)\\s*$/i.test(text)) continue;
                    const first = text.split('\\n')[0].trim();
                    if (first.length >= 8) { headline = first; break; }
                }
            }
            // Pass 2: legacy page-wide <p>-scan, but with post filtering.
            if (!headline) {
                const allPs = [...document.querySelectorAll('p')];
                for (const p of allPs) {
                    const text = (p.innerText || '').trim();
                    if (text.length < 15 || text.length > 300) continue;
                    if (_isPostLike(text)) continue;
                    if (text.includes('|') ||
                        /\\b(CEO|CTO|CIO|COO|CFO|VP|Director|Head|Manager|Engineer|Founder|Partner|Investor|Analyst|Advisor|Consultant)\\b/i.test(text)) {
                        headline = text; break;
                    }
                }
            }

            // About section — strict anchor on a <section> whose <h2> is
            // exactly "About". No longest-<p> fallback (that's how Tony's
            // and Maha's recent posts ended up as their summary).
            let summary = null;
            const aboutSection =
                document.querySelector('section[id*="about" i]') ||
                [...document.querySelectorAll('section')].find(s => {
                    const h = s.querySelector('h2');
                    return h && /^about$/i.test(h.innerText.trim());
                });
            if (aboutSection) {
                const candidates = [...aboutSection.querySelectorAll('p, span[class*="break"], div[class*="text"]')]
                    .map(el => el.innerText.trim())
                    .filter(t => t.length > 80 && !/^see (more|less)/i.test(t))
                    .sort((a, b) => b.length - a.length);
                if (candidates.length) summary = candidates[0];
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

            // Profile photo — scope strictly to the target profile's <main>
            // container. CRITICAL: LinkedIn shows the LOGGED-IN USER's
            // "Me" avatar in the global nav at the top-right of EVERY page,
            // and unscoped queries (May 11 incident) match that avatar
            // first, polluting hundreds of attendees with the operator's
            // own photo. We:
            //   1. Collect nav/header img srcs into a blacklist
            //   2. Search ONLY inside <main> for the target's photo
            //   3. Reject candidates whose src is in the nav blacklist
            //   4. Require alt-text or aria-label to mention the target's
            //      name as a final safety check
            let photoUrl = null;
            const targetName = (name || "").toLowerCase();
            const targetFirstName = targetName.split(/\\s+/)[0] || "";

            const navAvatarSrcs = new Set();
            for (const sel of ['header img', 'nav img', '.global-nav img', '#global-nav img']) {
                for (const img of document.querySelectorAll(sel)) {
                    if (img.src) navAvatarSrcs.add(img.src);
                }
            }

            // Photo extraction (v4): closest-common-ancestor primary +
            // LinkedIn preload-link fallback.
            //
            // PRIMARY (v3): among all profile-photo IMGs (page-wide search by
            // LinkedIn's unique URL pattern), pick the one whose DOM path
            // back up to a common ancestor with the profile owner's <h1> is
            // SHORTEST. Sidebar suggestion avatars share only `<main>` (or
            // higher) with the h1 and therefore have a longer path.
            //
            // FALLBACK (v4, 2026-05-19): when there's no <h1> in <main> the
            // primary returns null even though the photo is sitting in the
            // DOM (Sneha Yadamari — her top card rendered with a layout
            // variant that omits the in-main h1). Consult the
            // <link rel="preload" as="image" imagesrcset="...profile-displayphoto..."/>
            // that LinkedIn always emits in <head> for the top-card avatar.
            // That preload is the canonical top-card photo and survives
            // top-card layout variants.
            //
            // Defenses preserved against historical bugs:
            //   - May 11 nav-pollution: navAvatarSrcs blacklist filters out
            //     the operator's own "Me" avatar in the global nav.
            //   - Batch-5 sidebar-pollution: closest-ancestor rule picks the
            //     top-card photo over sidebar suggestions.
            //   - 2026-05-18 wrong-photo-on-no-photo: if NO profile-displayphoto
            //     imgs exist on the page AND no preload link, photo stays
            //     NULL. Never fall back to a guessed/operator avatar.
            // Reuse `ownerH1` from the headline-extraction block above.
            photoUrl = null;
            if (ownerH1) {
                const allPhotos = [...document.querySelectorAll(
                    'img[src*="profile-displayphoto"], img[src*="profile-framedphoto"]'
                )].filter(img => {
                    const src = img.src || '';
                    if (!src.startsWith('http')) return false;
                    if (navAvatarSrcs.has(src)) return false;
                    return true;
                });
                let bestPhoto = null;
                let bestDepth = Infinity;
                for (const img of allPhotos) {
                    // Walk up from the img until we find an ancestor that
                    // also contains the h1. Depth = number of steps up.
                    let depth = 0;
                    let ancestor = img;
                    while (ancestor && !ancestor.contains(ownerH1)) {
                        ancestor = ancestor.parentElement;
                        depth++;
                        if (depth > 20) break;  // safety cap
                    }
                    if (ancestor && depth < bestDepth) {
                        bestDepth = depth;
                        bestPhoto = img;
                    }
                }
                if (bestPhoto) photoUrl = bestPhoto.src;
            }

            // v4 fallback: preload-link signal. Only fires when the h1
            // anchor failed — keeps the 94 already-extracted profiles on
            // the proven v3 path.
            if (!photoUrl) {
                const preload = document.querySelector(
                    'link[imagesrcset*="profile-displayphoto"], link[imagesrcset*="profile-framedphoto"]'
                );
                if (preload) {
                    const srcset = preload.getAttribute('imagesrcset') || '';
                    // Format: "url 100w, url 200w, ..." — first entry is
                    // the _100_100 variant we store everywhere else.
                    const first = (srcset.split(',')[0] || '').trim();
                    const url = first.split(/\\s+/)[0];
                    if (url && url.startsWith('http') && !navAvatarSrcs.has(url)) {
                        photoUrl = url;
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


async def _search_linkedin(page, query: str, name: str) -> str | None:
    """Run a LinkedIn people-search for `query` and return the first profile URL
    whose surrounding text matches the attendee's first and last name tokens.

    Handles hyphenated last names (Romero-Finger), accented chars, and the
    /search/results/all fallback where LinkedIn sometimes redirects.
    """
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={query.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER"
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(3500)

        if "/login" in page.url or "/authwall" in page.url:
            return None

        return await page.evaluate("""(attendeeName) => {
            // Normalize: lowercase, strip accents, replace hyphens with space
            const norm = (s) => (s || "")
                .toLowerCase()
                .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
                .replace(/[-–—]/g, " ")
                .replace(/\\s+/g, " ")
                .trim();

            const parts = norm(attendeeName).split(/\\s+/).filter(p => p.length >= 2);
            if (parts.length < 2) return null;
            const firstName = parts[0];
            const lastName = parts[parts.length - 1];

            const links = [...document.querySelectorAll('a[href*="/in/"]')];
            for (const link of links) {
                const href = link.getAttribute('href') || '';
                if (!href.includes('/in/') || href.includes('/search/')) continue;

                // Look at an expanding neighbourhood: the link itself, its parent li,
                // and the enclosing search-result container.
                const containers = [
                    link,
                    link.closest('li'),
                    link.closest('[data-chameleon-result-urn]'),
                    link.closest('div[class*="entity"]'),
                    link.parentElement,
                ].filter(Boolean);

                for (const c of containers) {
                    const text = norm(c.innerText);
                    if (text.includes(firstName) && text.includes(lastName)) {
                        const match = href.match(/\\/in\\/([^/?]+)/);
                        if (match) return 'https://www.linkedin.com/in/' + match[1];
                    }
                }
            }
            return null;
        }""", name)
    except Exception as e:
        print(f"    Search error: {e}")
        return None


def _company_signal_set(attendee: dict) -> set[str]:
    """Build a set of lowercase tokens that should appear somewhere on the
    real candidate's LinkedIn page (headline / current-experience company)
    to verify they're actually the person we expected."""
    signals: set[str] = set()
    company = (attendee.get("company") or "").strip().lower()
    if company:
        # Strip common suffixes
        for suffix in (" inc", " ltd", " llc", " gmbh", " ag", " sa", " plc", " corp", " group"):
            if company.endswith(suffix):
                company = company[: -len(suffix)].strip()
        signals.add(company)
        # Space-collapsed variant so "X Ventures" (stored) matches "xventures"
        # on the page, and vice-versa (the haystack is also space-collapsed in
        # _verify_company_match). Fixes Karl Rusche ('xventures' vs "X Ventures")
        # and Nadine Gisdon ('wealth3capital' vs "Wealth3 Capital").
        if " " in company:
            signals.add(company.replace(" ", ""))
        # Also add first significant word ("Coinbase Asset Management" → "coinbase")
        first_word = company.split()[0] if company.split() else ""
        if len(first_word) >= 4:
            signals.add(first_word)

    email = (attendee.get("email") or "").strip().lower()
    if "@" in email:
        domain = email.split("@", 1)[1]
        slug = domain.split(".")[0].replace("-", "")  # xbto.com → xbto
        if slug and slug not in {"gmail", "yahoo", "hotmail", "outlook", "icloud", "proton", "protonmail"}:
            signals.add(slug)
    return {s for s in signals if len(s) >= 3}


def _verify_company_match(scraped: dict, signals: set[str]) -> tuple[bool, str | None]:
    """Return (matched, evidence_string). True if any signal token appears in
    the scraped headline or in any of the top experiences' company/title."""
    if not signals:
        # No company signal to verify against — fall back to accepting
        # (the existing first/last-name verification on _search_linkedin
        # already filtered to plausible candidates).
        return True, "no_company_signal"
    haystack = " ".join([
        (scraped.get("headline") or ""),
        (scraped.get("summary") or "")[:300],
        " ".join(
            f"{e.get('title','')} {e.get('company','') or ''}"
            for e in (scraped.get("experiences") or [])[:3]
        ),
    ]).lower()
    # Space-collapsed haystack so a space-free stored company ('xventures')
    # matches a spaced page rendering ("X Ventures"). Substring check runs
    # against both the original and the collapsed text.
    haystack_nospace = haystack.replace(" ", "")
    for s in signals:
        if s in haystack or s.replace(" ", "") in haystack_nospace:
            return True, f"signal '{s}' matched"
    return False, f"no signal in {sorted(signals)} matched scraped data"


async def discover_linkedin_url(page, name: str, company: str) -> str | None:
    """Find a LinkedIn profile by searching LinkedIn people-search.

    Strategy:
      1. name + company (full query, if company is present)
      2. name only (fallback — handles email-derived 'companies' like
         'Catierf' that narrow the search too much)
    """
    parts = name.lower().split()
    if len(parts) < 2:
        return None

    # Strategy 1: name + company
    if company:
        url = await _search_linkedin(page, f"{name} {company}", name)
        if url:
            return url

    # Strategy 2: name only (always run as fallback)
    return await _search_linkedin(page, name, name)


def _is_already_enriched(attendee: dict) -> bool:
    """An attendee is 'already enriched' if their enriched_profile.linkedin
    has a real headline (not the empty stub returned for private/403 profiles).
    """
    li = (attendee.get("enriched_profile") or {}).get("linkedin") or {}
    return bool(li.get("headline"))


async def run(dry_run: bool, limit: int | None, discover: bool, only_missing: bool = False, include_enriched: bool = False, verify_company: bool = True, missing_photos_only: bool = False, names: list[str] | None = None):
    print("=== LinkedIn Profile Scraper (Playwright) ===\n")

    # Fetch attendees
    if missing_photos_only:
        # Target only rows with linkedin_url set AND photo_url IS NULL.
        # Bypasses the _is_already_enriched skip so we re-visit profiles
        # that have LinkedIn data already but never captured a photo.
        attendees_with_url = fetch_attendees(with_url_only=True, missing_photo_only=True)
        attendees_without_url = []
        print(f"  Attendees missing photos (linkedin_url set, photo_url NULL): {len(attendees_with_url)}")
    elif discover:
        attendees = fetch_attendees(with_url_only=False)
        attendees_with_url = [a for a in attendees if a.get("linkedin_url")]
        attendees_without_url = [a for a in attendees if not a.get("linkedin_url")]
        print(f"  Attendees with LinkedIn URL: {len(attendees_with_url)}")
        print(f"  Attendees without URL (will try discovery): {len(attendees_without_url)}")
    else:
        attendees_with_url = fetch_attendees(with_url_only=True)
        attendees_without_url = []
        print(f"  Attendees with LinkedIn URL: {len(attendees_with_url)}")

    # Default: skip attendees who already have non-stub LinkedIn data —
    # cheaper, kinder to LinkedIn rate limits, and the common case.
    # Override with --include-enriched to force re-scrape.
    # --missing-photos-only bypasses this skip — the WHOLE POINT of that
    # mode is to re-scrape profiles that DO have linkedin data but no photo.
    if not include_enriched and not missing_photos_only:
        before_with = len(attendees_with_url)
        before_without = len(attendees_without_url)
        attendees_with_url = [a for a in attendees_with_url if not _is_already_enriched(a)]
        attendees_without_url = [a for a in attendees_without_url if not _is_already_enriched(a)]
        skipped_enriched = (before_with - len(attendees_with_url)) + (before_without - len(attendees_without_url))
        if skipped_enriched:
            print(f"  Skipping {skipped_enriched} already-enriched (use --include-enriched to re-scrape)")

    # In discover mode, process discovery candidates first, then existing URLs
    if only_missing:
        all_targets = attendees_without_url  # retry just the failures
        print(f"  Mode: --only-missing — retrying {len(all_targets)} attendees without URLs")
    else:
        all_targets = attendees_without_url + attendees_with_url if discover else attendees_with_url + attendees_without_url
    # --names filter (case-insensitive substring match against attendee.name)
    # for surgical re-scrapes without burning through the queue.
    if names:
        name_set = [n.lower() for n in names]
        all_targets = [a for a in all_targets if any(n in (a.get("name") or "").lower() for n in name_set)]
        print(f"  --names filter matched: {len(all_targets)}")
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
            url_was_discovered = False
            if not linkedin_url and discover:
                print(f"  [{i+1}/{len(all_targets)}] {name} — discovering URL...")
                linkedin_url = await discover_linkedin_url(
                    page, name, attendee.get("company", "")
                )
                if linkedin_url:
                    print(f"    Found: {linkedin_url}")
                    url_was_discovered = True
                    # Patch URL only after company verification (below) when in
                    # --verify-company mode. Without verification, we patch
                    # immediately like before.
                    if not verify_company:
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

                # Company-signal verification — now enforced on EVERY scrape,
                # not just auto-discovered URLs. The 2026-05-18 batch produced
                # multiple wrong-person attributions because URLs constructed
                # from name slugs (e.g. /in/pavankaur, /in/juanbruce) are not
                # unique and were collected without verification — Pavan Kaur
                # at Rulespark was scraped as "Graduate at NUS"; tony
                # mclaughlin at Ubyx was scraped as a generic "Operations
                # manager". The verification compares the attendee's company
                # name against the scraped headline / summary / experience
                # company fields.
                #
                # On verification failure: mark the row with
                # `enriched_profile.linkedin_unscrapable=verification_failed`
                # so the script auto-skips it in future batches until an
                # operator fixes the URL. --no-verify-company opts out.
                signals = _company_signal_set(attendee)
                matched, evidence = _verify_company_match(data, signals)
                if verify_company and not matched:
                    print(f"    ❌ Company verify failed: {evidence}")
                    print(f"       scraped headline: {(data.get('headline') or '')[:80]}")
                    if not dry_run:
                        # Preserve scraped data under linkedin_unverified so
                        # the operator can review what was actually scraped.
                        # The matching engine reads `linkedin` (not
                        # `linkedin_unverified`), so this data has no effect
                        # until an operator promotes it.
                        ep = dict(attendee.get("enriched_profile") or {})
                        ep["linkedin_unverified"] = data
                        ep["linkedin_unscrapable"] = "verification_failed"
                        ep["linkedin_verify_failed_at"] = __import__("datetime").datetime.utcnow().isoformat()
                        ep["linkedin_verify_evidence"] = evidence
                        patch_attendee(attendee["id"], {"enriched_profile": ep})
                    skipped_count += 1
                    await asyncio.sleep(DELAY_SECONDS)
                    continue
                if url_was_discovered:
                    print(f"    🔎 Company verify ok: {evidence}")
                    discovered_count += 1
                    if not dry_run:
                        patch_attendee(attendee["id"], {"linkedin_url": linkedin_url})

                print(f"    ✅ {data['headline'][:60]}")
                print(f"    📷 photo_url: {data.get('profile_pic_url') or 'NULL'}")
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
                        # Bumped 1500 → 2500 chars on 2026-05-15 — bios
                        # like Chiara's (2417) were still cut. If we DO
                        # need to truncate, cut at the last sentence
                        # boundary (./!/?) before the cap so the admin
                        # "Enriched Data" panel never ends mid-word. An
                        # explicit "…" marks the truncation.
                        raw = data["summary"]
                        if len(raw) <= 2500:
                            summary_parts.append(raw)
                        else:
                            head = raw[:2500]
                            cut = max(head.rfind("."), head.rfind("!"), head.rfind("?"))
                            if cut < 1200:
                                cut = 2500
                            summary_parts.append(head[: cut + 1] + " …")
                    enriched["linkedin_summary"] = " | ".join(summary_parts)

                    patch_payload = {"enriched_profile": enriched}

                    # Auto-fill title if empty
                    if not attendee.get("title") and data.get("experiences"):
                        patch_payload["title"] = data["experiences"][0].get("title", "")

                    # Auto-fill photo
                    if data.get("profile_pic_url"):
                        patch_payload["photo_url"] = data["profile_pic_url"]

                    # Backfill surname when DB has only a first name. The
                    # speaker-sheet sync sometimes lands rows like
                    # name="Gavin" (Gavin Zaentz on LinkedIn), which makes
                    # them undiscoverable by full-name search in the app.
                    # Prefer the scraped page-title name; fall back to
                    # title-casing the URL slug if that's missing.
                    db_name = (attendee.get("name") or "").strip()
                    if db_name and " " not in db_name:
                        candidate = (data.get("scraped_name") or "").strip()
                        if not candidate:
                            slug = linkedin_url.rstrip("/").split("/in/")[-1].split("/")[0]
                            slug = slug.split("?")[0]
                            if slug and "-" in slug:
                                candidate = " ".join(p.capitalize() for p in slug.split("-"))
                        if (
                            candidate
                            and " " in candidate
                            and candidate.split()[0].lower() == db_name.lower()
                        ):
                            patch_payload["name"] = candidate
                            print(f"    📝 Name backfilled: '{db_name}' → '{candidate}'")

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
    parser.add_argument("--verify-company", dest="verify_company", action="store_true", default=True, help="(default on) Reject scrapes whose page doesn't mention the attendee's company name or email-domain slug. On failure, flag the row enriched_profile.linkedin_unscrapable=verification_failed so it's skipped in future batches. Use --no-verify-company to disable.")
    parser.add_argument("--no-verify-company", dest="verify_company", action="store_false", help="Disable company-name verification. Useful when an operator has manually curated URLs they want to trust without a company-text check.")
    parser.add_argument("--only-missing", action="store_true", help="Only process attendees without linkedin_url (retry failed discoveries, skip the ones we already have)")
    parser.add_argument("--include-enriched", action="store_true", help="Re-scrape attendees who already have LinkedIn data (default: skip them)")
    parser.add_argument("--missing-photos-only", action="store_true", help="Only scrape rows where linkedin_url is set AND photo_url is NULL. Targets photo gaps without re-touching profiles that already have a photo.")
    parser.add_argument("--names", nargs="+", help="Case-insensitive substring filter on attendee.name. Targets a specific subset without burning through the queue (e.g. --names josiah luca).")
    args = parser.parse_args()

    # --only-missing implies --discover
    discover = args.discover or args.only_missing
    asyncio.run(run(dry_run=args.dry_run, limit=args.limit, discover=discover, only_missing=args.only_missing, include_enriched=args.include_enriched, verify_company=args.verify_company, missing_photos_only=args.missing_photos_only, names=args.names))
