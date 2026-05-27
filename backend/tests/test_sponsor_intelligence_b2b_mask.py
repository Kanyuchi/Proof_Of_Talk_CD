"""Pin the b2b mask on the sponsor intelligence GPT-4o prompt.

Second LLM-facing surface flagged after 6965805: `_generate_explanations`
in app/services/sponsor_intelligence.py builds an `Attendee {i+1}:` block
per candidate and feeds Name/Title/Goals/AI Summary into the GPT-4o
prompt with no privacy gate. The pre-fix loop wrote the raw name + title
+ first-200-chars of goals/ai_summary for every candidate, including
privacy_mode='b2b_only' attendees - same leak class as the matching
prompt, different LLM surface.

Scope for this fix: mask the LLM-facing prompt only. The structured
response data (attendees + explanations) returned to the admin dashboard
stays untouched - sponsor reports are admin-only and the admin already
has full attendee visibility via /attendees/*. The risk we're closing is
the LLM seeing the company<->person mapping and referencing the real
name in its free-text output (key_evidence, why_they_matter, etc.).
"""
from app.services.sponsor_intelligence import _describe_attendee_block


def _attendee_dict(name="Marcello Mari", company="AIVM", privacy_mode="b2b_only", **overrides):
    """Match the shape that _find_relevant_attendees produces."""
    base = {
        "name": name,
        "title": "CEO",
        "company": company,
        "ticket_type": "DELEGATE",
        "goals": "Marcello is looking to partner with custody providers.",
        "ai_summary": "Marcello Mari is the CEO of AIVM, formerly of SingularityNET.",
        "vertical_tags": ["ai_depin_frontier_tech"],
        "intent_tags": ["seeking_partners"],
        "deal_readiness": 0.6,
        "similarity": 0.82,
        "privacy_mode": privacy_mode,
    }
    base.update(overrides)
    return base


def test_attendee_block_for_full_profile_keeps_real_name():
    """Baseline: full-profile attendees still feed real name + title + raw
    goals/summary into the prompt. Most rows hit this path."""
    a = _attendee_dict(
        name="Marc Taverner", company="Polaris", privacy_mode="full",
        title="Partner", goals="Raising a $50M fund.",
        ai_summary="Marc Taverner runs Polaris.",
    )
    block = _describe_attendee_block(a, position=0)
    assert "Name: Marc Taverner" in block
    assert "Title: Partner" in block
    assert "Marc Taverner" in block  # raw name preserved in summary line too


def test_attendee_block_for_b2b_uses_company_in_name_slot():
    """b2b attendee: the labelled Name slot must be the company, not the
    real person. Sponsor-side LLM has no path to learn AIVM=Marcello."""
    a = _attendee_dict()
    block = _describe_attendee_block(a, position=0)
    assert "Name: AIVM" in block
    assert "Marcello" not in block, f"first name leaked:\n{block}"
    assert "Mari" not in block, f"surname leaked:\n{block}"


def test_attendee_block_blanks_title_for_b2b():
    """Title can carry identifying info ('CEO at AIVM' style) - blank for b2b,
    same convention as the matching candidate block."""
    a = _attendee_dict(title="CEO")
    block = _describe_attendee_block(a, position=0)
    # Title line present but value blank
    assert "Title: \n" in block or "Title:\n" in block


def test_attendee_block_masks_real_name_inside_goals_and_summary_for_b2b():
    """The truncated goals/ai_summary fields are where the name most often
    leaks (e.g. 'Marcello is looking to ...'). Mask must apply before the
    200-char slice so we don't leave half a name behind."""
    a = _attendee_dict()
    block = _describe_attendee_block(a, position=0)
    assert "Marcello" not in block
    assert "Mari" not in block
    # Original meaning survives via the company referent.
    assert "AIVM" in block


def test_attendee_block_does_not_touch_third_party_names_for_b2b():
    """Privacy is about THIS attendee's identity. Third parties named in
    goals/summary (co-founders, target sectors) stay readable."""
    a = _attendee_dict(
        goals="Marcello co-founded SingularityNET with Ben Goertzel.",
        ai_summary="Mari leads AIVM, partnering with Vitalik's foundations.",
    )
    block = _describe_attendee_block(a, position=0)
    assert "Marcello" not in block
    assert "Mari" not in block
    assert "SingularityNET" in block
    assert "Ben Goertzel" in block
    assert "Vitalik" in block


def test_attendee_block_handles_b2b_without_company_set():
    """Defensive: b2b without company shouldn't happen by UX design.
    _display_name returns empty; mask helper falls back to 'the company'."""
    a = _attendee_dict(company="", goals="Marcello pitched yesterday.")
    block = _describe_attendee_block(a, position=0)
    assert "Marcello" not in block


def test_attendee_block_respects_200_char_truncation_after_masking():
    """The pre-fix code applied [:200] truncation to goals/ai_summary. The
    mask must apply BEFORE truncation, and the truncation must still cap
    the resulting field so prompt size stays bounded."""
    long_goals = "Marcello " + ("blah " * 100)  # > 200 chars
    a = _attendee_dict(goals=long_goals)
    block = _describe_attendee_block(a, position=0)
    assert "Marcello" not in block
    # Look at the Goals line specifically and confirm it's truncated.
    goals_line = next(line for line in block.split("\n") if line.strip().startswith("Goals:"))
    goals_value = goals_line.split("Goals:", 1)[1].strip()
    assert len(goals_value) <= 200
