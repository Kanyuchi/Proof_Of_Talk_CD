import httpx
import structlog
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

        # Run enrichment sources (gracefully handle failures)
        if attendee.linkedin_url and settings.PROXYCURL_API_KEY:
            linkedin_data = await self._enrich_linkedin(attendee.linkedin_url)
            if linkedin_data:
                enriched["linkedin"] = linkedin_data
                enriched["linkedin_summary"] = self._summarize_linkedin(linkedin_data)

        if attendee.twitter_handle and settings.TWITTER_BEARER_TOKEN:
            twitter_data = await self._enrich_twitter(attendee.twitter_handle)
            if twitter_data:
                enriched["twitter"] = twitter_data
                enriched["recent_activity"] = self._summarize_twitter(twitter_data)

        if attendee.company_website:
            website_data = await self._scrape_company_website(attendee.company_website)
            if website_data:
                enriched["website"] = website_data
                enriched["company_description"] = website_data.get("description", "")

        return enriched

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

    async def close(self):
        await self.http_client.aclose()
