"""Pure-function tests for the reciprocity backlog script."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import notify_pending_interest as npi  # noqa: E402


def test_compute_incoming_counts_pending_side():
    matches = [
        {"attendee_a_id": "A", "attendee_b_id": "B", "status_a": "pending", "status_b": "accepted"},
        {"attendee_a_id": "A", "attendee_b_id": "C", "status_a": "pending", "status_b": "accepted"},
        {"attendee_a_id": "D", "attendee_b_id": "A", "status_a": "accepted", "status_b": "pending"},
        {"attendee_a_id": "X", "attendee_b_id": "Y", "status_a": "accepted", "status_b": "accepted"},
    ]
    inc = npi._compute_incoming(matches)
    assert inc["A"] == 3          # B, C, and D all accepted A; A still pending
    assert "D" not in inc         # D accepted, waiting on A — not an incoming request
    assert "X" not in inc         # already mutual


def test_classify_excludes_demo_optout_notoken_and_no_incoming():
    attendees = [
        {"id": "A", "email": "a@x.com", "magic_access_token": "t", "email_opt_out": False},
        {"id": "B", "email": "b@demo.proofoftalk.io", "magic_access_token": "t", "email_opt_out": False},
        {"id": "C", "email": "c@x.com", "magic_access_token": "t", "email_opt_out": True},
        {"id": "D", "email": "d@x.com", "magic_access_token": None, "email_opt_out": False},
        {"id": "E", "email": "e@x.com", "magic_access_token": "t", "email_opt_out": False},
    ]
    incoming = {"A": 2, "B": 1, "C": 1, "D": 1}   # E has no incoming
    out = npi._classify(attendees, incoming, ledger=set())
    assert [a["id"] for a in out["eligible"]] == ["A"]
    assert out["eligible"][0]["_incoming"] == 2
    assert out["skipped"]["demo"] == 1
    assert out["skipped"]["opted_out"] == 1
    assert out["skipped"]["no_token"] == 1
    assert out["skipped"]["no_incoming"] == 1


def test_classify_respects_ledger():
    attendees = [{"id": "A", "email": "a@x.com", "magic_access_token": "t", "email_opt_out": False}]
    out = npi._classify(attendees, {"A": 1}, ledger={"a@x.com"})
    assert out["eligible"] == []
    assert out["skipped"]["already_sent"] == 1
