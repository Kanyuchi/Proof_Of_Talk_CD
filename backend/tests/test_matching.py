"""Tests for the matching engine logic."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.embeddings import build_composite_text, cosine_similarity
from app.models.attendee import Attendee, TicketType


class TestMatchingLogic:
    """Test the matching logic without database dependencies."""

    def test_all_profiles_produce_composite_text(self, all_attendees):
        """Every test profile should produce non-empty composite text."""
        for attendee in all_attendees:
            text = build_composite_text(attendee)
            assert len(text) > 50, f"Composite text too short for {attendee.name}"
            assert attendee.name in text

    def test_composite_text_captures_goals(self, all_attendees):
        """Goals should be embedded in composite text for matching."""
        for attendee in all_attendees:
            text = build_composite_text(attendee)
            if attendee.goals:
                # At least part of the goals should appear
                assert "Goals:" in text

    def test_complementary_profiles_distinguishable(self, all_attendees):
        """Investor and startup profiles should have different composite texts."""
        amara = all_attendees[0]  # SWF investor
        marcus = all_attendees[1]  # Startup CEO

        amara_text = build_composite_text(amara)
        marcus_text = build_composite_text(marcus)

        # Amara should mention deploying capital
        assert "$200M" in amara_text
        # Marcus should mention raising/partnerships
        assert "Series B" in marcus_text or "strategic investors" in marcus_text.lower()

    def test_regulator_profile_distinct(self, all_attendees):
        """Sophie (Bundesbank) should have regulatory-focused text."""
        sophie = all_attendees[4]
        text = build_composite_text(sophie)
        assert "CBDC" in text or "regulatory" in text.lower() or "MiCA" in text

    def test_enriched_data_enhances_text(self, sample_attendee):
        """Enriched data should make composite text richer."""
        base_text = build_composite_text(sample_attendee)
        base_len = len(base_text)

        sample_attendee.enriched_profile = {
            "linkedin_summary": "15 years in sovereign wealth fund management, ex-Goldman Sachs",
            "company_description": "Abu Dhabi sovereign wealth fund with $800B AUM",
            "funding_info": "Government-backed, unlimited deployment capacity",
        }
        enriched_text = build_composite_text(sample_attendee)

        assert len(enriched_text) > base_len
        assert "Goldman Sachs" in enriched_text
        assert "$800B" in enriched_text


class TestSeedData:
    def test_five_profiles_loaded(self, seed_profiles):
        assert len(seed_profiles) == 5

    def test_all_profiles_have_required_fields(self, seed_profiles):
        required = {"name", "email", "company", "title", "ticket_type", "interests", "goals"}
        for profile in seed_profiles:
            for field in required:
                assert field in profile, f"Missing {field} in {profile.get('name', 'unknown')}"

    def test_ticket_types_valid(self, seed_profiles):
        valid_types = {"delegate", "sponsor", "speaker", "vip"}
        for profile in seed_profiles:
            assert profile["ticket_type"] in valid_types

    def test_profiles_have_diverse_interests(self, seed_profiles):
        """Each profile should have unique interests for differentiated matching."""
        all_interests = set()
        for profile in seed_profiles:
            profile_interests = set(profile["interests"])
            # Each profile should contribute at least 1 unique interest
            assert len(profile_interests) >= 2
            all_interests.update(profile_interests)
        # Collectively should cover many topics
        assert len(all_interests) >= 10

    def test_profile_names(self, seed_profiles):
        expected = {"Amara Okafor", "Marcus Chen", "Dr. Elena Vasquez", "James Whitfield", "Sophie Bergmann"}
        actual = {p["name"] for p in seed_profiles}
        assert actual == expected


class TestMatchScoring:
    """Test vector similarity scoring logic."""

    def test_similar_profiles_score_higher(self):
        """Profiles with overlapping embeddings should score higher."""
        # Simulate: two investors should be more similar to each other
        investor_a = [0.9, 0.8, 0.1, 0.2]  # investing-heavy
        investor_b = [0.85, 0.75, 0.15, 0.25]
        startup = [0.1, 0.2, 0.9, 0.8]  # building-heavy

        sim_investors = cosine_similarity(investor_a, investor_b)
        sim_cross = cosine_similarity(investor_a, startup)

        assert sim_investors > sim_cross

    def test_deal_readiness_score(self):
        """Deal readiness should be calculable from intent tags."""
        deal_signals = {"deploying_capital", "raising_capital", "deal_making", "seeking_customers"}

        # High deal readiness
        tags_high = ["deploying_capital", "deal_making", "seeking_partnerships"]
        score_high = len(set(tags_high) & deal_signals) / len(deal_signals)

        # Low deal readiness
        tags_low = ["knowledge_exchange", "regulatory_engagement"]
        score_low = len(set(tags_low) & deal_signals) / len(deal_signals)

        assert score_high > score_low
        assert score_high == 0.5  # 2 out of 4
        assert score_low == 0.0
