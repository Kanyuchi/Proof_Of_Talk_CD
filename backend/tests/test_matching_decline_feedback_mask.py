"""Pin the b2b mask on the decline_feedback block of rank_and_explain.

Third leak surface flagged after 6965805: the PRIOR FEEDBACK section that
feeds the target attendee's earlier decline reasons back into the GPT-4o
prompt was writing the raw `other.name` of every previously-declined
counterpart, plus the verbatim decline_reason text. Both leak the real
name when the counterpart was privacy_mode='b2b_only'. This file pins
the fix: the same _display_name + _mask_text_for_candidate helpers used
in the candidate-description block are applied here too.
"""
from types import SimpleNamespace

from app.services.matching import MatchingEngine


def _b2b(name: str, company: str):
    return SimpleNamespace(name=name, company=company, privacy_mode="b2b_only")


def _full(name: str, company: str = ""):
    return SimpleNamespace(name=name, company=company, privacy_mode="full")


def test_decline_feedback_line_for_full_profile_counterpart_uses_real_name():
    """Baseline: non-b2b counterparts keep the real name in the line, same
    as the pre-fix shape. This is the contract for the majority of rows."""
    other = _full("Marc Taverner", "Polaris")
    line = MatchingEngine._format_decline_feedback_entry(
        other, "not raising in our sector",
    )
    assert line == "- Declined Marc Taverner: not raising in our sector"


def test_decline_feedback_line_for_b2b_counterpart_uses_company_name():
    """b2b counterpart: the labelled name slot must be the company, not the
    real person. The LLM must not learn that Company=AIVM corresponds to
    Person=Marcello via the feedback loop."""
    other = _b2b("Marcello Mari", "AIVM")
    line = MatchingEngine._format_decline_feedback_entry(
        other, "wrong stage for us",
    )
    assert "Marcello" not in line
    assert "Mari" not in line
    assert "Declined AIVM:" in line


def test_decline_feedback_masks_real_name_inside_the_decline_reason_text():
    """Defense in depth: the decline_reason is freeform text the target
    wrote. They may have written the b2b person's real name in it (if they
    learned it offline, e.g. through a shared connection). The mask must
    redact any occurrence of the b2b counterpart's name in the reason text
    too, not just the labelled slot."""
    other = _b2b("Marcello Mari", "AIVM")
    line = MatchingEngine._format_decline_feedback_entry(
        other, "Marcello pitched me last year, same product",
    )
    assert "Marcello" not in line, f"name leaked inside reason: {line!r}"
    assert "Mari" not in line
    # The reason content survives (so the LLM still gets the signal "same
    # product, declined before").
    assert "pitched me last year" in line
    assert "same product" in line


def test_decline_feedback_handles_none_counterpart_gracefully():
    """If the counterpart row is gone (deleted attendee), keep the
    pre-fix Unknown fallback so the prompt still has the decline_reason
    signal without crashing."""
    line = MatchingEngine._format_decline_feedback_entry(
        None, "wrong sector",
    )
    assert line == "- Declined Unknown: wrong sector"


def test_decline_feedback_handles_b2b_with_empty_company():
    """Edge case: b2b counterpart with no company set. _display_name returns
    empty, so the line falls back to 'Unknown' rather than leaving the real
    name visible."""
    other = SimpleNamespace(name="Marcello Mari", company="", privacy_mode="b2b_only")
    line = MatchingEngine._format_decline_feedback_entry(
        other, "wrong stage",
    )
    assert "Marcello" not in line
    assert "Mari" not in line
    assert "Declined Unknown:" in line


def test_decline_feedback_handles_missing_decline_reason():
    """decline_reason can legitimately be None / empty (rare but valid)."""
    other = _b2b("Marcello Mari", "AIVM")
    line = MatchingEngine._format_decline_feedback_entry(other, None)
    assert "Marcello" not in line
    assert "Mari" not in line
    assert line.startswith("- Declined AIVM:")


def test_decline_feedback_does_not_touch_third_party_names_in_reason():
    """Privacy promise is about THIS counterpart's identity. Third-party
    names mentioned in the decline_reason (e.g. a co-investor referenced by
    name) stay readable so the LLM gets the full signal."""
    other = _b2b("Marcello Mari", "AIVM")
    line = MatchingEngine._format_decline_feedback_entry(
        other, "competitive with Vitalik's portfolio company",
    )
    assert "Vitalik" in line
    assert "Marcello" not in line
