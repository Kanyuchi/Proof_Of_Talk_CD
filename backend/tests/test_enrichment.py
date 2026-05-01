"""Tests for the enrichment service."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.enrichment import EnrichmentService
from app.models.attendee import Attendee, TicketType


@pytest.fixture
def enrichment_service():
    return EnrichmentService()


@pytest.fixture
def attendee_with_urls():
    return Attendee(
        name="Marcus Chen",
        email="marcus@vaultbridge.example",
        company="VaultBridge",
        title="CEO & Co-Founder",
        ticket_type=TicketType.SPEAKER,
        interests=["institutional custody"],
        goals="Looking for strategic investors",
        linkedin_url="https://linkedin.com/in/marcuschen",
        twitter_handle="@marcuschen",
        company_website="https://vaultbridge.example",
        enriched_profile={},
        intent_tags=[],
    )


class TestEnrichmentService:
    def test_summarize_linkedin(self, enrichment_service):
        data = {
            "headline": "CEO at VaultBridge",
            "summary": "Building institutional custody infrastructure",
            "experiences": [{"title": "CEO", "company": "VaultBridge"}],
            "skills": ["Blockchain", "DeFi", "Custody"],
        }
        result = enrichment_service._summarize_linkedin(data)
        assert "CEO at VaultBridge" in result
        assert "Blockchain" in result

    def test_summarize_twitter(self, enrichment_service):
        data = {
            "bio": "Building the future of custody",
            "recent_tweets": ["Excited about tokenization!", "MiCA changes everything"],
        }
        result = enrichment_service._summarize_twitter(data)
        assert "custody" in result
        assert "tokenization" in result

    def test_summarize_linkedin_empty(self, enrichment_service):
        result = enrichment_service._summarize_linkedin({})
        assert result == ""

    def test_summarize_twitter_empty(self, enrichment_service):
        result = enrichment_service._summarize_twitter({})
        assert result == ""


class TestWebsiteScraping:
    @pytest.mark.asyncio
    async def test_scrape_success(self, enrichment_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <title>VaultBridge - Institutional Custody</title>
                <meta name="description" content="Enterprise custody for tokenised securities">
            </head>
            <body><p>Leading custody platform</p></body>
        </html>
        """

        with patch.object(
            enrichment_service.http_client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await enrichment_service._scrape_company_website("https://vaultbridge.example")

        assert result is not None
        assert "VaultBridge" in result["title"]
        assert "custody" in result["description"].lower()

    @pytest.mark.asyncio
    async def test_scrape_failure(self, enrichment_service):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(
            enrichment_service.http_client, "get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await enrichment_service._scrape_company_website("https://nonexistent.example")

        assert result is None


# Proxycurl-based LinkedIn tests removed 2026-05-01 — Proxycurl was sunset
# (returns 410) and the linkedin-api fallback was retired after LinkedIn
# started 403'ing the account. Bulk LinkedIn enrichment now lives in the
# manual Playwright script at scripts/linkedin_scrape.py.
