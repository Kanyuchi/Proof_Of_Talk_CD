"""Pin the b2b_only field-level mask for free-text candidate fields.

Follow-up to 13d35a0: the Name + Title mask kept the labelled identity off
the LLM input, but the free-text fields (AI Summary, Goals, Grid context
description) still re-stated the real person's name verbatim. This file
pins the field-level redaction that closes that gap.

Scope: redact the *candidate's own* real name (full, first, last) from
free-text fields when privacy_mode='b2b_only'. Third-party names mentioned
in the text are left alone (they're not the privacy promise we made).
"""
from types import SimpleNamespace

from app.services.matching import MatchingEngine


def _b2b(name: str, company: str):
    return SimpleNamespace(name=name, company=company, privacy_mode="b2b_only")


def _full(name: str, company: str = ""):
    return SimpleNamespace(name=name, company=company, privacy_mode="full")


# ── _mask_text_for_candidate ──────────────────────────────────────────────


def test_mask_passes_through_for_non_b2b_candidates():
    """Full-profile candidates: the LLM is allowed to see their real name in
    free-text. Mask must be a no-op."""
    cand = _full("Marc Taverner", "Polaris")
    text = "Marc Taverner runs Polaris and has been raising for 18 months."
    assert MatchingEngine._mask_text_for_candidate(text, cand) == text


def test_mask_replaces_full_name_in_b2b_text():
    """The most common AI-summary leak: the full name appears verbatim."""
    cand = _b2b("Marcello Mari", "AIVM")
    text = "Marcello Mari is the CEO of AIVM, building privacy-preserving AI custody."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert "Marcello Mari" not in out
    assert "AIVM" in out  # company is the replacement, still present


def test_mask_replaces_first_name_used_standalone():
    """Second sentence pattern: 'Marcello previously worked at ...'."""
    cand = _b2b("Marcello Mari", "AIVM")
    text = "AIVM is a privacy-preserving AI startup. Marcello previously co-founded SingularityNET."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert "Marcello" not in out
    # Underlying content (the SingularityNET reference) survives — useful for matching.
    assert "SingularityNET" in out


def test_mask_replaces_last_name_used_standalone():
    """Less common but real: 'Mari has spent 8 years in AI'."""
    cand = _b2b("Marcello Mari", "AIVM")
    text = "Mari has spent 8 years in AI / Web3."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert "Mari" not in out
    assert "AIVM" in out


def test_mask_is_case_insensitive():
    cand = _b2b("Marcello Mari", "AIVM")
    text = "marcello mari is building MARCELLO's vision."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert "arcello" not in out.lower()  # both forms gone


def test_mask_uses_word_boundaries_so_short_tokens_dont_clobber():
    """A 2-char first name like 'Bo' must NOT be substituted at the word
    level — it would clobber every English word containing 'bo'. The full
    name still gets replaced; the short token is the conservative skip."""
    cand = _b2b("Bo Hines", "Brick")
    text = "Bo Hines is into bonds and bourbon and rebooting infrastructure."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    # Full name gone
    assert "Bo Hines" not in out
    # Common words ("bonds", "bourbon", "rebooting") untouched
    assert "bonds" in out and "bourbon" in out and "rebooting" in out
    # Last name (>= 3 chars) standalone gone
    assert "Hines" not in out


def test_mask_handles_empty_or_none_text():
    cand = _b2b("Marcello Mari", "AIVM")
    assert MatchingEngine._mask_text_for_candidate("", cand) == ""
    assert MatchingEngine._mask_text_for_candidate(None, cand) == ""


def test_mask_handles_b2b_with_empty_company_without_crashing():
    """Defensive: b2b without a company shouldn't happen by UX design, but
    don't blow up the prompt build if it does. Replacement falls back to a
    generic placeholder rather than leaving the name visible."""
    cand = SimpleNamespace(name="Marcello Mari", company="", privacy_mode="b2b_only")
    text = "Marcello Mari leads the team."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert "Marcello Mari" not in out
    assert "Marcello" not in out
    assert "Mari" not in out


def test_mask_does_not_touch_third_party_names_mentioned_in_text():
    """Privacy promise is about THIS candidate's identity, not anyone they
    mention. 'Co-founded with Vitalik' should stay readable for matching."""
    cand = _b2b("Marcello Mari", "AIVM")
    text = "Marcello co-founded SingularityNET with Ben Goertzel before starting AIVM."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert "Ben Goertzel" in out
    assert "SingularityNET" in out
    assert "Marcello" not in out


def test_mask_handles_multi_word_name_without_double_substitution():
    """Longest-first replacement so 'Marcello Mari' is replaced as a unit and
    we don't then re-replace 'Marcello' and 'Mari' inside the substituted
    company name."""
    cand = _b2b("Marcello Mari", "AIVM")
    text = "Marcello Mari and Marcello Mari again."
    out = MatchingEngine._mask_text_for_candidate(text, cand)
    assert out == "AIVM and AIVM again."


# ── Smoke-level integration: the three named fields ──────────────────────


def test_mask_applies_cleanly_to_each_of_the_three_named_fields():
    """The three fields called out in the 2026-05-27 follow-up: AI Summary,
    Goals, and the Grid context blob. All three must come out clean."""
    cand = _b2b("Marcello Mari", "AIVM")
    ai_summary = "Marcello Mari is the CEO of AIVM, formerly of SingularityNET."
    goals = "Marcello is looking to partner with custody providers in Europe."
    grid_context = "Grid Verified: AIVM is led by Marcello Mari and builds privacy-preserving AI."

    for src in (ai_summary, goals, grid_context):
        out = MatchingEngine._mask_text_for_candidate(src, cand)
        assert "Marcello" not in out, f"name leaked in: {out!r}"
        assert "Mari" not in out, f"surname leaked in: {out!r}"


# ── Wiring pin: the prompt block actually uses the mask ──────────────────


def _full_b2b_candidate():
    """A fully-populated b2b candidate the way rank_and_explain sees them."""
    return SimpleNamespace(
        name="Marcello Mari",
        title="CEO",
        company="AIVM",
        privacy_mode="b2b_only",
        goals="Marcello is looking to partner with custody providers in Europe.",
        ai_summary="Marcello Mari is the CEO of AIVM, formerly of SingularityNET.",
        interests=["custody", "privacy"],
        intent_tags=["seeking_partners"],
        vertical_tags=["ai_depin_frontier_tech"],
        deal_readiness_score=0.6,
        inferred_customer_profile={},
        enriched_profile={"grid": {
            "grid_name": "AIVM",
            "grid_description": "AIVM is led by Marcello Mari and builds privacy-preserving AI.",
            "grid_sector": "ai",
        }},
    )


def test_describe_candidate_does_not_leak_b2b_name_into_any_free_text_field():
    """Wiring pin: when the prompt-build helper renders a b2b candidate, the
    real name must not appear anywhere in the resulting block — not in the
    Name/Title slots (display_name + blanked title) and not in the free-text
    Goals / AI Summary / Grid lines. If a future refactor drops the mask
    call from any of those, this test fails."""
    cand = _full_b2b_candidate()
    block = MatchingEngine._describe_candidate(
        cand, sim_score=0.82, position=0, target_icp_keywords=set(),
    )
    assert "Marcello" not in block, f"first name leaked:\n{block}"
    assert "Mari" not in block, f"last name leaked:\n{block}"
    # The masked referent (company) should be present so the LLM has someone
    # to write about.
    assert "AIVM" in block
    # The Name: slot must be the company, not the real person.
    assert "Name: AIVM" in block
    # The Title: slot must be blanked for b2b.
    assert "Title: \n" in block


def test_describe_candidate_does_not_leak_b2b_name_when_company_is_empty():
    """Edge case: a b2b candidate without a company set must NOT fall back
    to the real name in the Name slot. _display_name returns "" in that
    case; the block helper must use a safe sentinel, not candidate.name."""
    cand = SimpleNamespace(
        name="Marcello Mari",
        title="CEO",
        company="",  # empty
        privacy_mode="b2b_only",
        goals="Marcello is looking to partner.",
        ai_summary="Marcello Mari built AIVM.",
        interests=[],
        intent_tags=[],
        vertical_tags=[],
        deal_readiness_score=0.5,
        inferred_customer_profile={},
        enriched_profile={},
    )
    block = MatchingEngine._describe_candidate(
        cand, sim_score=0.7, position=0, target_icp_keywords=set(),
    )
    assert "Marcello" not in block, f"name leaked despite empty company:\n{block}"
    assert "Mari" not in block, f"surname leaked despite empty company:\n{block}"


def test_describe_candidate_preserves_full_profile_for_non_b2b():
    """Sanity: the mask is a no-op for full-profile candidates — the real
    name still appears in Name/AI Summary/Goals/Grid so the LLM has the
    richest signal."""
    cand = SimpleNamespace(
        name="Marc Taverner",
        title="Partner",
        company="Polaris",
        privacy_mode="full",
        goals="Marc is raising a $50M fund for tokenized credit.",
        ai_summary="Marc Taverner runs Polaris, ex-Bitfury head of comms.",
        interests=["rwa"],
        intent_tags=["raising_capital"],
        vertical_tags=["investment_and_capital_markets"],
        deal_readiness_score=0.7,
        inferred_customer_profile={},
        enriched_profile={"grid": {
            "grid_name": "Polaris",
            "grid_description": "Polaris is a tokenization fund led by Marc Taverner.",
        }},
    )
    block = MatchingEngine._describe_candidate(
        cand, sim_score=0.77, position=2, target_icp_keywords=set(),
    )
    assert "Name: Marc Taverner" in block
    assert "Title: Partner" in block
    assert "Marc Taverner" in block  # raw name preserved in summary/grid lines
