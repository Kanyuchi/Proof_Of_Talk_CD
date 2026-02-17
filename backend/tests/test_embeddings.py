"""Tests for the embeddings service."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.embeddings import (
    build_composite_text,
    cosine_similarity,
    generate_embedding,
    generate_ai_summary,
    classify_intents,
)
from app.models.attendee import Attendee, TicketType


class TestBuildCompositeText:
    def test_includes_basic_fields(self, sample_attendee):
        text = build_composite_text(sample_attendee)
        assert "Amara Okafor" in text
        assert "Director of Digital Assets" in text
        assert "Abu Dhabi Sovereign Wealth Fund" in text
        assert "vip" in text.lower()

    def test_includes_interests(self, sample_attendee):
        text = build_composite_text(sample_attendee)
        assert "tokenised real-world assets" in text
        assert "blockchain infrastructure" in text

    def test_includes_goals(self, sample_attendee):
        text = build_composite_text(sample_attendee)
        assert "$200M" in text

    def test_includes_enriched_data(self, sample_attendee):
        sample_attendee.enriched_profile = {
            "linkedin_summary": "Experienced digital assets leader",
            "company_description": "Sovereign wealth fund managing $800B",
        }
        text = build_composite_text(sample_attendee)
        assert "Experienced digital assets leader" in text
        assert "Sovereign wealth fund" in text

    def test_includes_ai_summary(self, sample_attendee):
        sample_attendee.ai_summary = "Senior allocator with $200M mandate"
        text = build_composite_text(sample_attendee)
        assert "Senior allocator" in text

    def test_handles_empty_fields(self):
        attendee = Attendee(
            name="Test",
            email="test@test.com",
            company="TestCo",
            title="Tester",
            ticket_type=TicketType.DELEGATE,
            interests=[],
            goals=None,
            enriched_profile={},
            intent_tags=[],
        )
        text = build_composite_text(attendee)
        assert "Test" in text
        assert "TestCo" in text


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_similar_vectors(self):
        a = [1.0, 1.0, 0.0]
        b = [1.0, 0.8, 0.1]
        score = cosine_similarity(a, b)
        assert 0.9 < score < 1.0


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_calls_openai(self):
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

        with patch("app.services.embeddings.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            result = await generate_embedding("test text")

        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once()


class TestGenerateAiSummary:
    @pytest.mark.asyncio
    async def test_returns_summary(self, sample_attendee):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Senior allocator with $200M mandate for tokenised RWA."))
        ]

        with patch("app.services.embeddings.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = await generate_ai_summary(sample_attendee)

        assert "200M" in result
        assert isinstance(result, str)


class TestClassifyIntents:
    @pytest.mark.asyncio
    async def test_returns_intent_list(self, sample_attendee):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='["deploying_capital", "technology_evaluation"]'))
        ]

        with patch("app.services.embeddings.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = await classify_intents(sample_attendee)

        assert "deploying_capital" in result
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self, sample_attendee):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="not valid json"))
        ]

        with patch("app.services.embeddings.client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            result = await classify_intents(sample_attendee)

        assert result == ["knowledge_exchange"]
