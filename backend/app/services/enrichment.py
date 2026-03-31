import httpx
import structlog
import re
from datetime import datetime
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class EnrichmentService:
    """Multi-source data enrichment pipeline for attendee profiles."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "POTMatchmaker/1.0"},
        )

    async def enrich_attendee(self, attendee) -> dict:
        """Run all enrichment sources and merge results."""
        enriched = attendee.enriched_profile or {}

        # --- LinkedIn enrichment ---
        # Step 1: resolve URL if not already stored
        linkedin_url = attendee.linkedin_url
        if not linkedin_url and settings.LINKEDIN_LI_AT_COOKIE:
            linkedin_url = await self._find_linkedin_url_by_email(attendee.email, attendee.name or "")
        if not linkedin_url and settings.LINKEDIN_LI_AT_COOKIE and attendee.name and attendee.company:
            linkedin_url = await self._find_linkedin_url_by_name(attendee.name, attendee.company)

        # Step 2: fetch profile data
        if linkedin_url:
            linkedin_data = None
            if settings.PROXYCURL_API_KEY:
                linkedin_data = await self._enrich_linkedin(linkedin_url)
            elif settings.LINKEDIN_LI_AT_COOKIE:
                linkedin_data = await self._enrich_linkedin_voyager(linkedin_url)
            if linkedin_data:
                if not attendee.linkedin_url:
                    attendee.linkedin_url = linkedin_url
                enriched["linkedin"] = linkedin_data
                enriched["linkedin_summary"] = self._summarize_linkedin(linkedin_data)
                enriched["linkedin_enriched_at"] = datetime.utcnow().isoformat()
                # Auto-populate photo_url from LinkedIn if not already set
                pic = linkedin_data.get("profile_pic_url")
                if pic and not attendee.photo_url:
                    attendee.photo_url = pic

        if attendee.twitter_handle and settings.TWITTER_BEARER_TOKEN:
            twitter_data = await self._enrich_twitter(attendee.twitter_handle)
            if twitter_data:
                enriched["twitter"] = twitter_data
                enriched["recent_activity"] = self._summarize_twitter(twitter_data)
                enriched["twitter_enriched_at"] = datetime.utcnow().isoformat()

        if attendee.company_website:
            website_data = await self._scrape_company_website(attendee.company_website)
            if website_data:
                enriched["website"] = website_data
                enriched["company_description"] = website_data.get("description", "")
                enriched["website_enriched_at"] = datetime.utcnow().isoformat()

        if attendee.company:
            crunchbase_data = await self._enrich_crunchbase(attendee.company, attendee.company_website)
            if crunchbase_data:
                enriched["crunchbase"] = crunchbase_data
                enriched["crunchbase_enriched_at"] = datetime.utcnow().isoformat()

        # --- The Grid B2B enrichment (Web3 company database) ---
        if attendee.company and not enriched.get("grid"):
            from app.services.grid_enrichment import enrich_from_grid
            grid_data = await enrich_from_grid(attendee.company)
            if grid_data:
                enriched["grid"] = grid_data
                enriched["grid_enriched_at"] = datetime.utcnow().isoformat()

        return enriched

    def _voyager_headers(self) -> dict:
        """Build headers required for LinkedIn Voyager dash API calls."""
        return {
            "Cookie": f"li_at={settings.LINKEDIN_LI_AT_COOKIE}; JSESSIONID=\"{settings.LINKEDIN_CSRF_TOKEN}\"",
            "csrf-token": settings.LINKEDIN_CSRF_TOKEN,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "x-restli-protocol-version": "2.0.0",
            "x-li-lang": "en_US",
        }

    async def _find_linkedin_url_by_email(self, email: str, attendee_name: str = "") -> str | None:
        """
        Derive a LinkedIn vanity URL from an email address.
        Only accepts candidates where the identifier contains both the attendee's
        first and last name — prevents short/ambiguous matches like 'dariia-p'.
        """
        try:
            # Require a recognisable first+last name in the identifier
            name_parts = attendee_name.lower().split() if attendee_name else []
            if len(name_parts) < 2:
                return None  # Can't validate without full name
            first, last = name_parts[0], name_parts[-1]

            local = email.split("@")[0].lower()
            clean = re.sub(r"[._+]", "-", local)
            stripped = re.sub(r"\d+$", "", clean).rstrip("-")
            candidates = [c for c in [clean, stripped] if c]

            for candidate in candidates:
                # Reject if candidate doesn't contain both first and last name
                if first not in candidate or last not in candidate:
                    continue
                if await self._verify_linkedin_identifier(candidate):
                    logger.info("linkedin_url_found_by_email", email=email, identifier=candidate)
                    return f"https://www.linkedin.com/in/{candidate}"
        except Exception as e:
            logger.error("linkedin_email_lookup_error", error=str(e), email=email)
        return None

    async def _find_linkedin_url_by_name(self, name: str, company: str) -> str | None:
        """
        Derive a LinkedIn vanity URL from a full name (first-last pattern only).
        Only tries candidates that contain both first and last name — rejects
        short patterns like 'f-lastname' that are too ambiguous.
        """
        try:
            parts = name.lower().split()
            if len(parts) < 2:
                return None
            first, last = parts[0], parts[-1]
            # Only try the full first-last combo; single-initial patterns are too ambiguous
            candidates = [f"{first}-{last}"]
            for candidate in candidates:
                if await self._verify_linkedin_identifier(candidate):
                    logger.info("linkedin_url_found_by_name", name=name, identifier=candidate)
                    return f"https://www.linkedin.com/in/{candidate}"
        except Exception as e:
            logger.error("linkedin_name_search_error", error=str(e), name=name, company=company)
        return None

    async def _verify_linkedin_identifier(self, identifier: str) -> bool:
        """Return True if the given public identifier resolves to a real LinkedIn profile."""
        try:
            resp = await self.http_client.get(
                "https://www.linkedin.com/voyager/api/identity/dash/profiles",
                params={
                    "q": "memberIdentity",
                    "memberIdentity": identifier,
                    "decorationId": "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-86",
                },
                headers=self._voyager_headers(),
                follow_redirects=True,
            )
            # 200 = found, 403 = found but private, 404 = not found
            return resp.status_code in (200, 403)
        except Exception:
            return False

    async def _enrich_linkedin_voyager(self, linkedin_url: str) -> dict | None:
        """
        Fetch LinkedIn profile data via the Voyager dash/profiles endpoint.
        Response structure: {"data": {...}, "included": [...typed objects...]}
        Profile, Position, Education items are in the flat `included` array.
        """
        try:
            match = re.search(r"/in/([^/?#]+)", linkedin_url)
            if not match:
                logger.warning("linkedin_voyager_bad_url", url=linkedin_url)
                return None
            profile_id = match.group(1)

            resp = await self.http_client.get(
                "https://www.linkedin.com/voyager/api/identity/dash/profiles",
                params={
                    "q": "memberIdentity",
                    "memberIdentity": profile_id,
                    "decorationId": "com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-86",
                },
                headers=self._voyager_headers(),
                follow_redirects=True,
            )
            if resp.status_code not in (200, 403):
                logger.warning("linkedin_voyager_fetch_failed", status=resp.status_code, profile=profile_id)
                return None
            if resp.status_code == 403:
                # Profile exists but is private — return minimal stub so URL gets saved
                logger.info("linkedin_profile_private", profile=profile_id)
                return {"headline": None, "summary": None, "experiences": [], "skills": [],
                        "education": [], "source": "voyager_private"}

            data = resp.json()
            included = data.get("included", [])

            # Pull typed objects out of the flat included array
            profile_obj = next(
                (i for i in included if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Profile"),
                {}
            )
            positions = [
                i for i in included
                if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Position"
            ]
            skills = [
                i for i in included
                if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Skill"
            ]
            educations = [
                i for i in included
                if i.get("$type") == "com.linkedin.voyager.dash.identity.profile.Education"
            ]

            experiences = [
                {
                    "title": pos.get("title"),
                    "company": pos.get("companyName"),
                    "description": pos.get("description"),
                }
                for pos in positions[:5]
            ]

            # Extract photo URL from profilePicture -> vectorImage artifacts
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
                    # Pick the largest artifact
                    largest = max(artifacts, key=lambda a: a.get("width", 0))
                    profile_pic_url = root_url + largest.get("fileIdentifyingUrlPathSegment", "")
            except Exception:
                pass

            return {
                "headline": profile_obj.get("headline"),
                "summary": profile_obj.get("summary"),
                "profile_pic_url": profile_pic_url,
                "experiences": experiences,
                "skills": [s.get("name") for s in skills[:15] if s.get("name")],
                "education": [
                    {
                        "school": edu.get("schoolName"),
                        "degree": edu.get("degreeName"),
                        "field": edu.get("fieldOfStudy"),
                    }
                    for edu in educations[:3]
                ],
                "source": "voyager",
            }
        except Exception as e:
            logger.error("linkedin_voyager_error", error=str(e), url=linkedin_url)
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def _enrich_linkedin(self, linkedin_url: str) -> dict | None:
        """Fetch LinkedIn profile data via Proxycurl API."""
        try:
            response = await self.http_client.get(
                "https://nubela.co/proxycurl/api/v2/linkedin",
                params={"linkedin_profile_url": linkedin_url},
                headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "headline": data.get("headline"),
                    "summary": data.get("summary"),
                    "profile_pic_url": data.get("profile_pic_url"),
                    "experiences": [
                        {
                            "title": exp.get("title"),
                            "company": exp.get("company"),
                            "description": exp.get("description"),
                        }
                        for exp in (data.get("experiences") or [])[:5]
                    ],
                    "skills": data.get("skills", [])[:15],
                    "education": [
                        {
                            "school": edu.get("school"),
                            "degree": edu.get("degree_name"),
                            "field": edu.get("field_of_study"),
                        }
                        for edu in (data.get("education") or [])[:3]
                    ],
                    "follower_count": data.get("follower_count"),
                }
            logger.warning("linkedin_enrichment_failed", status=response.status_code, url=linkedin_url)
            return None
        except Exception as e:
            logger.error("linkedin_enrichment_error", error=str(e), url=linkedin_url)
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def _enrich_twitter(self, handle: str) -> dict | None:
        """Fetch recent tweets and profile info from Twitter/X API v2."""
        handle = handle.lstrip("@")
        try:
            # Get user info
            user_resp = await self.http_client.get(
                f"https://api.twitter.com/2/users/by/username/{handle}",
                params={"user.fields": "description,public_metrics,created_at"},
                headers={"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"},
            )
            if user_resp.status_code != 200:
                return None

            user_data = user_resp.json().get("data", {})
            user_id = user_data.get("id")

            # Get recent tweets
            tweets_resp = await self.http_client.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                params={"max_results": 10, "tweet.fields": "text,created_at,public_metrics"},
                headers={"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"},
            )
            tweets = []
            if tweets_resp.status_code == 200:
                tweets = [t.get("text", "") for t in tweets_resp.json().get("data", [])]

            return {
                "bio": user_data.get("description"),
                "followers": user_data.get("public_metrics", {}).get("followers_count"),
                "recent_tweets": tweets[:5],
            }
        except Exception as e:
            logger.error("twitter_enrichment_error", error=str(e), handle=handle)
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def _scrape_company_website(self, url: str) -> dict | None:
        """Scrape company website for about page, product descriptions."""
        try:
            response = await self.http_client.get(url, follow_redirects=True)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract meta description
            meta_desc = ""
            meta_tag = soup.find("meta", attrs={"name": "description"})
            if meta_tag:
                meta_desc = meta_tag.get("content", "")

            # Extract title
            title = soup.title.string.strip() if soup.title else ""

            # Extract main text content (first 2000 chars)
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)[:2000]

            return {
                "title": title,
                "description": meta_desc or text[:300],
                "full_text": text,
            }
        except Exception as e:
            logger.error("website_scrape_error", error=str(e), url=url)
            return None

    def _summarize_linkedin(self, data: dict) -> str:
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

    def _summarize_twitter(self, data: dict) -> str:
        """Create a text summary from Twitter data."""
        parts = []
        if data.get("bio"):
            parts.append(f"Bio: {data['bio']}")
        if data.get("recent_tweets"):
            parts.append(f"Recent topics: {' | '.join(data['recent_tweets'][:3])}")
        return ". ".join(parts)

    async def _enrich_crunchbase(self, company_name: str, website: str | None = None) -> dict | None:
        """Fetch funding and company data from Crunchbase Basic API or by scraping."""
        # Try Crunchbase Basic API first (if key is available)
        if settings.CRUNCHBASE_API_KEY:
            try:
                slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
                resp = await self.http_client.get(
                    f"https://api.crunchbase.com/api/v4/entities/organizations/{slug}",
                    params={
                        "user_key": settings.CRUNCHBASE_API_KEY,
                        "field_ids": "short_description,funding_total,last_funding_type,"
                                     "last_funding_at,num_funding_rounds,investor_identifiers,"
                                     "categories,rank_org",
                    },
                )
                if resp.status_code == 200:
                    props = resp.json().get("properties", {})
                    return {
                        "description": props.get("short_description"),
                        "total_funding": props.get("funding_total", {}).get("value_usd"),
                        "last_funding_type": props.get("last_funding_type"),
                        "last_funding_date": props.get("last_funding_at"),
                        "funding_rounds": props.get("num_funding_rounds"),
                        "investors": [
                            i.get("value") for i in (props.get("investor_identifiers") or [])[:5]
                        ],
                        "categories": [
                            c.get("value") for c in (props.get("categories") or [])[:5]
                        ],
                        "source": "crunchbase_api",
                    }
            except Exception as e:
                logger.warning("crunchbase_api_error", error=str(e), company=company_name)

        # Fallback: scrape public Crunchbase page
        try:
            slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
            resp = await self.http_client.get(
                f"https://www.crunchbase.com/organization/{slug}",
                headers={"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"},
                follow_redirects=True,
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                # Extract meta description which usually contains funding/description info
                meta = soup.find("meta", attrs={"name": "description"})
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                description = (
                    (meta and meta.get("content"))
                    or (og_desc and og_desc.get("content"))
                    or ""
                )
                if description and len(description) > 30:
                    return {
                        "description": description[:500],
                        "source": "crunchbase_scrape",
                        "profile_url": f"https://www.crunchbase.com/organization/{slug}",
                    }
        except Exception as e:
            logger.warning("crunchbase_scrape_error", error=str(e), company=company_name)

        return None

    async def close(self):
        await self.http_client.aclose()
