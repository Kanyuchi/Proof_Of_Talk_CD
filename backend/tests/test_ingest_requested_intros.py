# backend/tests/test_ingest_requested_intros.py
"""Unit tests for scripts/ingest_requested_intros.py.

Mirrors the mock-DB convention of test_adoption_endpoint.py — no fixtures,
no real DB. The script is split into pure helpers + an async main(); the
helpers are tested directly and main() is exercised against an AsyncMock db.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import importlib.util
from pathlib import Path

# Load the script as a module (it lives under scripts/, not in the app package).
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ingest_requested_intros.py"
_spec = importlib.util.spec_from_file_location("ingest_requested_intros", _SCRIPT)
ingest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ingest)


# ---------------------------------------------------------------------------
# Fixtures: tiny in-memory attendee pool
# ---------------------------------------------------------------------------

def _att(name, company, title="", aid=None):
    return SimpleNamespace(id=aid or uuid4(), name=name, company=company, title=title)


# ---------------------------------------------------------------------------
# Markdown row parsing
# ---------------------------------------------------------------------------

def test_split_markdown_row_strips_cells():
    cells = ingest.split_markdown_row("| Amundi | Portfolio Manager | Aylin Zanier | reason |")
    assert cells == ["Amundi", "Portfolio Manager", "Aylin Zanier", "reason"]


def test_split_markdown_row_non_table_returns_empty():
    assert ingest.split_markdown_row("plain text line") == []
    assert ingest.split_markdown_row("") == []


def test_is_separator_row_detects_alignment_cells():
    assert ingest.is_separator_row([":-:", ":-:", ":-:"])
    assert ingest.is_separator_row(["---", "---"])
    assert not ingest.is_separator_row(["Amundi", "Portfolio Manager"])


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------

def test_detect_schema_aylin():
    header = ["Organization", "Job Title", "Request Meeting", "Reason for introduction."]
    assert ingest.detect_schema(header) == "aylin"


def test_detect_schema_ylli():
    header = [
        "Company", "ICP Segment", "HQ / Location", "Title(s) from List",
        "Priority Action", "Why Meet?", "",
    ]
    assert ingest.detect_schema(header) == "ylli"


def test_detect_schema_meeting_log_returns_none():
    # The Meeting Log header should NOT be picked up
    header = ["Meeting Type", "Date / Time", "First Name", "Last Name"]
    assert ingest.detect_schema(header) is None


# ---------------------------------------------------------------------------
# Full table parsing
# ---------------------------------------------------------------------------

def test_parse_tables_finds_aylin_block():
    text = """
| Organization | Job Title | Request Meeting | Reason for introduction. |
| :-: | :-: | :-: | :-: |
| Amundi | Portfolio Manager | Aylin Zanier | reason A |
| AXA | Project manager | Aylin Zanier | reason B |
""".strip().splitlines()
    tables = ingest.parse_tables(text)
    assert len(tables) == 1
    schema, rows = tables[0]
    assert schema == "aylin"
    assert len(rows) == 2
    assert rows[0][0] == "Amundi"


def test_parse_tables_skips_text_in_between_tables():
    text = """
| Organization | Job Title | Request Meeting | Reason for introduction. |
| :-: | :-: | :-: | :-: |
| Amundi | Portfolio Manager | Aylin Zanier | reason A |

some text not in a table

| Company | ICP Segment | HQ / Location | Title(s) from List | Priority Action | Why Meet? |  |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| LBBW | Bank / FI | Stuttgart | PM | Tier 2 | rationale | Ylli |
""".strip().splitlines()
    tables = ingest.parse_tables(text)
    assert [t[0] for t in tables] == ["aylin", "ylli"]


# ---------------------------------------------------------------------------
# Owner filtering
# ---------------------------------------------------------------------------

def test_extract_intro_rows_aylin_filters_by_owner():
    rows = [
        ["Amundi", "Portfolio Manager", "Aylin Zanier", "reason A"],
        ["Sketchy Co", "CEO", "Someone Else", "noise"],
        ["AXA", "PM", "aylin zanier", "reason C"],  # case-insensitive match
    ]
    out = ingest.extract_intro_rows("aylin", rows, "Aylin Zanier")
    assert [r.company for r in out] == ["Amundi", "AXA"]
    assert out[0].reason == "reason A"


def test_extract_intro_rows_ylli_drops_oliver_and_short_rows():
    rows = [
        ["LBBW", "Bank / FI", "Stuttgart", "PM", "Tier 2", "rationale", "Ylli"],
        ["FineryMkt", "Crypto Native", "London", "CEO", "Tier 2", "why", "Oliver"],
        ["Short", "row"],  # too few cols, dropped
    ]
    out = ingest.extract_intro_rows("ylli", rows, "Ylli")
    assert len(out) == 1
    assert out[0].company == "LBBW"
    assert out[0].title == "PM"


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def test_normalize_company_strips_suffix_and_punct():
    assert ingest.normalize_company("BNP Paribas") == ingest.normalize_company("bnpparibas")
    assert ingest.normalize_company("Elliptic Inc.") == "elliptic"


def test_fuzzy_company_candidates_exact_normalised_match_wins():
    attendees = [
        _att("Alice", "BNP Paribas"),
        _att("Bob", "BNPParibas"),
        _att("Carol", "Unrelated"),
    ]
    out = ingest.fuzzy_company_candidates("BNPParibas", attendees)
    names = [a.name for a in out]
    assert "Alice" in names and "Bob" in names
    assert "Carol" not in names


def test_fuzzy_company_candidates_threshold_filters_far_matches():
    attendees = [_att("Alice", "Completely Different Company")]
    out = ingest.fuzzy_company_candidates("Amundi", attendees)
    assert out == []


def test_narrow_by_title_picks_closest_title():
    a_ceo = _att("Alice", "Kiln", title="CEO")
    a_vp = _att("Bob", "Kiln", title="VP Special Projects")
    picked = ingest.narrow_by_title([a_ceo, a_vp], "VP Special Projects")
    assert picked is a_vp


def test_narrow_by_title_returns_first_when_target_blank():
    a1 = _att("Alice", "Kiln", title="CEO")
    picked = ingest.narrow_by_title([a1], "")
    assert picked is a1


def test_narrow_by_title_returns_none_when_no_title_clears_threshold():
    attendees = [
        _att("Alice", "Kiln", title="Janitor"),
        _att("Bob", "Kiln", title="Receptionist"),
    ]
    assert ingest.narrow_by_title(attendees, "CEO") is None


# ---------------------------------------------------------------------------
# build_target_name_raw
# ---------------------------------------------------------------------------

def test_build_target_name_raw_basic():
    assert ingest.build_target_name_raw("CEO", "Kiln") == "CEO at Kiln"


def test_build_target_name_raw_blanks_fallback():
    assert ingest.build_target_name_raw("", "Kiln") == "Unknown role at Kiln"
    assert ingest.build_target_name_raw("CEO", "") == "CEO at Unknown company"


# ---------------------------------------------------------------------------
# plan_intros — orchestrator
# ---------------------------------------------------------------------------

def test_plan_intros_matches_and_misses():
    requester_id = uuid4()
    target_attendee = _att("Erik Müller", "Kiln", title="CEO")
    attendees = [target_attendee, _att("Other", "DifferentCo", title="CTO")]
    rows = [
        ingest.IntroRow(company="Kiln", title="CEO", owner="Aylin Zanier"),
        ingest.IntroRow(company="GhostCo", title="Founder", owner="Aylin Zanier"),
    ]
    inserts, misses = ingest.plan_intros(rows, attendees, requester_id)

    assert len(inserts) == 2
    matched = next(r for r in inserts if r["target_company_raw"] == "Kiln")
    assert matched["target_attendee_id"] == target_attendee.id
    assert matched["target_name_raw"] == "CEO at Kiln"
    assert matched["source"] == ingest.SOURCE_TAG

    missed = next(r for r in inserts if r["target_company_raw"] == "GhostCo")
    assert missed["target_attendee_id"] is None
    assert missed["target_name_raw"] == "Founder at GhostCo"

    assert len(misses) == 1
    assert misses[0]["company"] == "GhostCo"


def test_plan_intros_multi_attendee_company_narrows_by_title():
    """When >1 attendee shares the same company, the title should pick the right one."""
    requester_id = uuid4()
    ceo = _att("Alice", "Kiln", title="CEO")
    vp = _att("Bob", "Kiln", title="VP Special Projects")
    rows = [
        ingest.IntroRow(company="Kiln", title="VP Special Projects", owner="x"),
    ]
    inserts, _misses = ingest.plan_intros(rows, [ceo, vp], requester_id)
    assert inserts[0]["target_attendee_id"] == vp.id


# ---------------------------------------------------------------------------
# main() smoke with mock DB — dry run (no --confirm)
# ---------------------------------------------------------------------------

class _Scalar:
    def __init__(self, v): self._v = v
    def scalars(self): return self
    def first(self): return self._v
    def all(self): return [self._v] if self._v is not None else []


class _Rows:
    def __init__(self, rows): self._rows = rows
    def scalars(self): return self
    def all(self): return self._rows


@pytest.mark.asyncio
async def test_main_dry_run_does_not_commit(tmp_path, monkeypatch, capsys):
    sheet = tmp_path / "sheet.md"
    sheet.write_text(
        "| Organization | Job Title | Request Meeting | Reason for introduction. |\n"
        "| :-: | :-: | :-: | :-: |\n"
        "| Amundi | Portfolio Manager | Aylin Zanier | reason A |\n"
    )

    requester = _att("Aylin Zanier", "Elliptic", title="BD", aid=uuid4())
    requester.email = "aylin.zanier@elliptic.co"
    target = _att("Some PM", "Amundi", title="Portfolio Manager")

    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(requester),    # _load_requester
        _Rows([requester, target]),  # _load_attendees
    ]

    # Patch async_session to return our mock db without touching real Postgres.
    class _Ctx:
        async def __aenter__(self_inner): return db
        async def __aexit__(self_inner, *a): return False

    monkeypatch.setattr(ingest, "async_session", lambda: _Ctx())

    args = SimpleNamespace(
        file=str(sheet),
        requester_email="aylin.zanier@elliptic.co",
        owner_label="Aylin Zanier",
        start_line=None,
        end_line=None,
        confirm=False,
    )
    rc = await ingest.main(args)
    assert rc == 0
    db.commit.assert_not_called()
    captured = capsys.readouterr().out
    assert "Dry run" in captured
    assert "1 matched to existing attendee" in captured


@pytest.mark.asyncio
async def test_main_confirm_commits_and_uses_on_conflict(tmp_path, monkeypatch):
    sheet = tmp_path / "sheet.md"
    sheet.write_text(
        "| Organization | Job Title | Request Meeting | Reason for introduction. |\n"
        "| :-: | :-: | :-: | :-: |\n"
        "| Amundi | Portfolio Manager | Aylin Zanier | reason A |\n"
    )

    requester = _att("Aylin Zanier", "Elliptic", title="BD", aid=uuid4())
    requester.email = "aylin.zanier@elliptic.co"

    db = AsyncMock()
    db.execute.side_effect = [
        _Scalar(requester),   # _load_requester
        _Rows([requester]),   # _load_attendees (no match for "Amundi")
        SimpleNamespace(rowcount=1),  # _insert_intros INSERT result
    ]

    class _Ctx:
        async def __aenter__(self_inner): return db
        async def __aexit__(self_inner, *a): return False

    monkeypatch.setattr(ingest, "async_session", lambda: _Ctx())

    args = SimpleNamespace(
        file=str(sheet),
        requester_email="aylin.zanier@elliptic.co",
        owner_label="Aylin Zanier",
        start_line=None,
        end_line=None,
        confirm=True,
    )
    rc = await ingest.main(args)
    assert rc == 0
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_unknown_requester_returns_error(tmp_path, monkeypatch):
    sheet = tmp_path / "sheet.md"
    sheet.write_text(
        "| Organization | Job Title | Request Meeting | Reason for introduction. |\n"
        "| :-: | :-: | :-: | :-: |\n"
        "| Amundi | PM | Aylin Zanier | x |\n"
    )

    db = AsyncMock()
    db.execute.side_effect = [_Scalar(None)]  # no requester found

    class _Ctx:
        async def __aenter__(self_inner): return db
        async def __aexit__(self_inner, *a): return False

    monkeypatch.setattr(ingest, "async_session", lambda: _Ctx())

    args = SimpleNamespace(
        file=str(sheet),
        requester_email="nobody@elliptic.co",
        owner_label="Aylin Zanier",
        start_line=None,
        end_line=None,
        confirm=False,
    )
    rc = await ingest.main(args)
    assert rc == 2


@pytest.mark.asyncio
async def test_main_returns_1_when_no_tables(tmp_path, monkeypatch):
    sheet = tmp_path / "sheet.md"
    sheet.write_text("just plain text\nno markdown tables here\n")

    args = SimpleNamespace(
        file=str(sheet),
        requester_email="x@y.co",
        owner_label="x",
        start_line=None,
        end_line=None,
        confirm=False,
    )
    rc = await ingest.main(args)
    assert rc == 1
