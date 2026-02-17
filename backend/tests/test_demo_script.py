"""Tests for the demo matching script — validates structure and logic without OpenAI calls."""
import pytest
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.demo_matching import (
    AttendeeProfile,
    MatchResult,
    build_composite_text,
    cosine_similarity,
)


@pytest.fixture
def demo_profiles():
    seed_file = Path(__file__).parent.parent / "data" / "seed_profiles.json"
    with open(seed_file) as f:
        raw = json.load(f)
    return [AttendeeProfile(**p) for p in raw]


class TestDemoDataStructures:
    def test_attendee_profile_creation(self, demo_profiles):
        assert len(demo_profiles) == 5
        for p in demo_profiles:
            assert p.name
            assert p.company
            assert p.title
            assert len(p.interests) >= 2

    def test_profile_defaults(self, demo_profiles):
        for p in demo_profiles:
            assert p.ai_summary == ""
            assert p.intent_tags == []
            assert p.deal_readiness == 0.0
            assert p.embedding == []

    def test_match_result_creation(self):
        m = MatchResult(
            attendee_a="Amara Okafor",
            attendee_b="Marcus Chen",
            similarity_score=0.85,
            complementary_score=0.92,
            overall_score=0.90,
            match_type="complementary",
            explanation="SWF deploying into tokenised RWA meets custody infrastructure builder.",
            shared_context={"sectors": ["tokenisation", "custody"]},
        )
        assert m.overall_score == 0.90
        assert m.match_type == "complementary"


class TestDemoCompositeText:
    def test_all_profiles_generate_text(self, demo_profiles):
        for p in demo_profiles:
            text = build_composite_text(p)
            assert len(text) > 50
            assert p.name in text
            assert p.company in text
            assert p.title in text

    def test_text_includes_goals(self, demo_profiles):
        amara = demo_profiles[0]
        text = build_composite_text(amara)
        assert "$200M" in text

    def test_text_with_ai_summary(self, demo_profiles):
        p = demo_profiles[0]
        p.ai_summary = "Senior sovereign wealth fund allocator with active mandate"
        text = build_composite_text(p)
        assert "Senior sovereign wealth fund" in text


class TestDemoSimilarityMatrix:
    def test_self_similarity_is_one(self):
        v = [0.1, 0.2, 0.3, 0.4, 0.5]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_pairwise_matrix_logic(self):
        """Simulate a 3-profile pairwise matrix."""
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.0, 0.0, 1.0],
        ]
        n = 3
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = cosine_similarity(embeddings[i], embeddings[j])

        # Profile 0 and 1 should be more similar than 0 and 2
        assert matrix[0][1] > matrix[0][2]
        # Matrix should be symmetric
        assert matrix[0][1] == pytest.approx(matrix[1][0])


class TestDemoExpectedMatches:
    """Validate that the 5 test profiles have expected characteristics for matching."""

    def test_amara_is_capital_deployer(self, demo_profiles):
        amara = demo_profiles[0]
        assert "Abu Dhabi" in amara.company
        assert "$200M" in amara.goals

    def test_marcus_is_fundraiser(self, demo_profiles):
        marcus = demo_profiles[1]
        assert "VaultBridge" in marcus.company
        assert "Series B" in marcus.goals or "strategic investors" in marcus.goals.lower()

    def test_elena_is_investor(self, demo_profiles):
        elena = demo_profiles[2]
        assert "Meridian" in elena.company
        assert "$500M" in elena.goals

    def test_james_is_builder(self, demo_profiles):
        james = demo_profiles[3]
        assert "NexaLayer" in james.company
        assert "compliance" in james.goals.lower() or "L2" in james.goals

    def test_sophie_is_regulator(self, demo_profiles):
        sophie = demo_profiles[4]
        assert "Bundesbank" in sophie.company
        assert "CBDC" in sophie.goals or "MiCA" in sophie.goals

    def test_amara_marcus_should_be_strong_match(self, demo_profiles):
        """Amara (SWF, $200M for tokenised RWA + custody) and Marcus (custody infra) should match."""
        amara, marcus = demo_profiles[0], demo_profiles[1]
        # Check overlapping concepts
        amara_text = (amara.goals + " " + " ".join(amara.interests)).lower()
        marcus_text = (marcus.goals + " " + " ".join(marcus.interests)).lower()
        # Both should mention custody/tokenisation
        assert "custody" in amara_text
        assert "custody" in marcus_text or "tokenised" in marcus_text

    def test_james_sophie_compliance_overlap(self, demo_profiles):
        """James (L2 + compliance modules) and Sophie (regulatory) share compliance focus."""
        james, sophie = demo_profiles[3], demo_profiles[4]
        james_text = (james.goals + " " + " ".join(james.interests)).lower()
        sophie_text = (sophie.goals + " " + " ".join(sophie.interests)).lower()
        assert "compliance" in james_text
        assert "regulatory" in sophie_text or "compliance" in sophie_text

    def test_elena_should_match_marcus(self, demo_profiles):
        """Elena (VC, TradFi-DeFi infra thesis, Series A-B) and Marcus (Series B, infra) should match."""
        elena, marcus = demo_profiles[2], demo_profiles[1]
        elena_text = (elena.goals + " " + " ".join(elena.interests)).lower()
        marcus_text = (marcus.goals + " " + " ".join(marcus.interests)).lower()
        assert "infrastructure" in elena_text or "series" in elena_text
        assert "series b" in marcus_text.lower() or "institutional" in marcus_text
