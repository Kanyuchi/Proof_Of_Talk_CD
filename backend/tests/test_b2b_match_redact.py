"""Pin the row-level transform used by the historical-leak redaction script.

Context: the LLM-side b2b mask shipped 2026-05-27 (6965805 + 9e6ccbe +
01b1457) prevents NEW leaks, but matches stored before those commits
still carry pre-fix explanation text with leaked names. The daily 03:30
UTC cron only generates matches for net-new attendees, so the historical
rows will never auto-refresh - they need a one-off redaction pass. This
module pins the pure row-level transform that pass uses.
"""
from types import SimpleNamespace

from app.services.b2b_match_redact import redact_b2b_in_match_fields


def _b2b(name="Marcello Mari", company="AIVM"):
    return SimpleNamespace(name=name, company=company, privacy_mode="b2b_only")


def _full(name="Marc Taverner", company="Polaris"):
    return SimpleNamespace(name=name, company=company, privacy_mode="full")


def test_returns_empty_for_non_b2b_counterpart():
    """No change requested when the joined attendee is not b2b_only."""
    full = _full()
    out = redact_b2b_in_match_fields(
        "Marc Taverner runs Polaris...", {}, full,
    )
    assert out == {}


def test_returns_empty_when_text_is_already_clean():
    """No leak in explanation or context -> no update emitted."""
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "AIVM is building privacy-preserving AI custody.",
        {"sectors": ["ai"], "synergies": ["AIVM has the product"], "action_items": ["Ask AIVM about ..."]},
        b2b,
    )
    assert out == {}


def test_masks_real_name_in_explanation():
    """The most common leak: real name appears in the stored explanation."""
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "Marcello Mari from AIVM is solving privacy in AI.",
        None,
        b2b,
    )
    assert "explanation" in out
    assert "Marcello" not in out["explanation"]
    assert "Mari" not in out["explanation"]
    assert "AIVM" in out["explanation"]


def test_masks_real_name_in_synergies_list():
    """shared_context.synergies is a list of strings the LLM wrote - names
    leak here too. The helper must mask each entry, returning the updated
    context dict only when something actually changed."""
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "AIVM and you both work on privacy.",
        {
            "sectors": ["ai", "privacy"],
            "synergies": [
                "Marcello has the product Karl needs",
                "AIVM's custody fits Karl's wallet",
            ],
            "action_items": ["Ask AIVM about their roadmap"],
        },
        b2b,
    )
    # explanation was clean, no change there
    assert "explanation" not in out
    assert "shared_context" in out
    masked_synergies = out["shared_context"]["synergies"]
    assert all("Marcello" not in s for s in masked_synergies)
    # Third-party reference (Karl) is preserved.
    assert any("Karl" in s for s in masked_synergies)
    # Untouched keys come through unchanged.
    assert out["shared_context"]["sectors"] == ["ai", "privacy"]


def test_masks_real_name_in_action_items_list():
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "Brief intro.",
        {"action_items": ["Pitch Marcello on the wallet integration"]},
        b2b,
    )
    assert "shared_context" in out
    items = out["shared_context"]["action_items"]
    assert all("Marcello" not in i for i in items)


def test_masks_name_in_both_explanation_and_context_simultaneously():
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "Marcello Mari leads AIVM.",
        {"synergies": ["Marcello and you both ship custody"]},
        b2b,
    )
    assert "explanation" in out
    assert "shared_context" in out
    assert "Marcello" not in out["explanation"]
    assert all("Marcello" not in s for s in out["shared_context"]["synergies"])


def test_does_not_touch_third_party_names_in_text():
    """Privacy promise is about THIS counterpart's identity. Third parties
    mentioned in explanation/synergies stay readable."""
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "Marcello co-founded SingularityNET with Ben Goertzel.",
        None,
        b2b,
    )
    assert "Marcello" not in out["explanation"]
    assert "Ben Goertzel" in out["explanation"]
    assert "SingularityNET" in out["explanation"]


def test_handles_b2b_with_empty_name_defensively():
    """If the b2b attendee somehow has an empty name, there's nothing to
    mask. Return empty (no change) rather than crash or no-op masking."""
    b2b = SimpleNamespace(name="", company="AIVM", privacy_mode="b2b_only")
    out = redact_b2b_in_match_fields(
        "Marcello Mari leads AIVM.", None, b2b,
    )
    assert out == {}


def test_handles_non_string_items_in_context_lists():
    """shared_context lists could theoretically contain non-strings from
    legacy data. Skip them without crashing."""
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        None,
        {"synergies": ["Marcello has X", 123, None, "AIVM has Y"]},
        b2b,
    )
    assert "shared_context" in out
    new = out["shared_context"]["synergies"]
    # The string with the leak got masked; non-strings stayed.
    assert "Marcello" not in (new[0] or "")
    assert new[1] == 123
    assert new[2] is None
    assert new[3] == "AIVM has Y"


def test_handles_null_shared_context():
    """shared_context can be None in legacy rows."""
    b2b = _b2b()
    out = redact_b2b_in_match_fields(
        "Marcello at AIVM.", None, b2b,
    )
    assert "shared_context" not in out
    assert "explanation" in out
