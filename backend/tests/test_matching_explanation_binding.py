"""Pin the contract that match explanations bind to the RIGHT candidate.

Bug reported by Arda Askin (Knidos) 2026-05-26: his #2 card showed AIVM but
the explanation talked about Michael Arrington at Arrington Capital. DB scan
found 4/6 of his top matches had explanation text referencing a completely
different person from the persisted attendee_b_id.

Root cause: _persist_ranked (and _deterministic_rerank) trusted the LLM's
1-based candidate_index. When the LLM put the wrong index on an entry (e.g.
because "candidate_index" was ambiguous between input-position and output-
rank), explanations and per-candidate score boosts got bound to the wrong
candidate. Fix: the LLM now also returns candidate_name verbatim, and a
re-anchoring step rewrites candidate_index from the input-list name lookup
before any downstream code uses it.
"""
from types import SimpleNamespace

import pytest

from app.services.matching import MatchingEngine


def _cand(name: str):
    return SimpleNamespace(name=name)


def test_realign_corrects_wrong_candidate_index_using_name():
    """LLM returned explanations for Rob and Ersoy but swapped the indices.
    Re-anchoring by candidate_name must restore the correct binding."""
    A = _cand("Rob Hadick"); B = _cand("Ersoy Kiraz")
    candidates = [(A, 0.9), (B, 0.8)]
    ranked = [
        {"candidate_index": 2, "candidate_name": "Rob Hadick",
         "explanation": "Rob Hadick from Dragonfly is a prime match..."},
        {"candidate_index": 1, "candidate_name": "Ersoy Kiraz",
         "explanation": "Ersoy Kiraz from Knidos..."},
    ]
    fixed = MatchingEngine._realign_entries_by_name(ranked, candidates)
    by_name = {e["candidate_name"]: e["candidate_index"] for e in fixed}
    assert by_name["Rob Hadick"] == 1, "Rob's explanation must point at input position 1"
    assert by_name["Ersoy Kiraz"] == 2, "Ersoy's explanation must point at input position 2"


def test_realign_drops_entries_whose_name_is_not_in_candidates():
    """If the LLM hallucinates a name not present in the input candidates,
    and supplies no usable fallback index, the entry must be dropped — not
    bound to a random candidate."""
    candidates = [(_cand("Real Person"), 0.9)]
    ranked = [
        {"candidate_index": 99, "candidate_name": "Hallucinated Name",
         "explanation": "..."},
    ]
    assert MatchingEngine._realign_entries_by_name(ranked, candidates) == []


def test_realign_falls_back_to_index_when_name_missing():
    """Legacy entries without candidate_name (pre-fix shape) must still bind
    via candidate_index so we don't lose matches during the rollout."""
    candidates = [(_cand("Alice"), 0.9), (_cand("Bob"), 0.8)]
    ranked = [{"candidate_index": 2, "explanation": "..."}]
    fixed = MatchingEngine._realign_entries_by_name(ranked, candidates)
    assert len(fixed) == 1
    assert fixed[0]["candidate_index"] == 2
