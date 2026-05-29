"""Ingest Elliptic priority-intro request rows from a markdown-exported sheet.

The "Proof of Talk Paris event booklet" Google Sheet
(1g40iZM_utxjG_aPzynDmOwny8g_iQKv0FAHyj6RWE5I) was exported as markdown
tables to /tmp/elliptic_sheet.txt. Each tab is a separate markdown table.
This script ingests ONE requester's tab per invocation:

    # dry-run (no DB writes)
    python scripts/ingest_requested_intros.py \
        --file /tmp/elliptic_sheet.txt \
        --requester-email aylin.zanier@elliptic.co \
        --owner-label "Aylin Zanier" \
        --start-line 136 --end-line 170

    # commit
    python scripts/ingest_requested_intros.py \
        --file /tmp/elliptic_sheet.txt \
        --requester-email ylli@elliptic.co \
        --owner-label "Ylli" \
        --start-line 763 --end-line 795 \
        --confirm

Schema auto-detect:
    - "Organization | Job Title | Request Meeting | Reason for introduction."
      -> AYLIN (4 cols, owner col index 2)
    - "Company | ICP Segment | HQ / Location | Title(s) from List
       | Priority Action | Why Meet? | (owner)"
      -> YLLI (7 cols, owner col index 6)

For each data row whose owner column matches --owner-label, the script:
    - Fuzzy-matches Company against attendees.company.
    - If >1 candidate, narrows by Title against attendees.title.
    - Builds target_name_raw = "{Title} at {Company}" (sheet has no person name).
    - Inserts a RequestedIntro row with the matched target_attendee_id (or NULL
      on a miss). Source tag fixed to 'elliptic_intro_request_2026_05_29'.

Idempotent via the unique constraint on
(requester_attendee_id, target_name_raw, target_company_raw): re-runs are no-ops.
"""
import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Attendee, RequestedIntro  # noqa: E402

SOURCE_TAG = "elliptic_intro_request_2026_05_29"
COMPANY_MATCH_THRESHOLD = 0.85
TITLE_MATCH_THRESHOLD = 0.55

AYLIN_HEADER = ("organization", "job title", "request meeting", "reason for introduction.")
YLLI_HEADER_PREFIX = ("company", "icp segment", "hq / location")  # owner is col 6


@dataclass
class IntroRow:
    company: str
    title: str
    owner: str
    reason: str | None = None  # Aylin schema only


# ---------------------------------------------------------------------------
# Pure helpers — fully testable without a DB
# ---------------------------------------------------------------------------

def split_markdown_row(line: str) -> list[str]:
    """Split a `| a | b | c |` markdown row into trimmed cells."""
    # Strip leading/trailing `|`, then split on `|`
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return []
    inner = s[1:-1]
    return [c.strip() for c in inner.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    """A markdown separator row has only `:-:` / `---` style cells."""
    if not cells:
        return False
    return all(re.fullmatch(r":?-+:?", c.strip()) for c in cells)


def detect_schema(header_cells: list[str]) -> str | None:
    """Return 'aylin' or 'ylli' if the header matches one of the known schemas."""
    lowered = tuple(c.lower().strip() for c in header_cells)
    if len(lowered) >= 4 and lowered[:4] == AYLIN_HEADER:
        return "aylin"
    if len(lowered) >= 6 and lowered[:3] == YLLI_HEADER_PREFIX:
        return "ylli"
    return None


def parse_tables(lines: list[str]) -> list[tuple[str, list[list[str]]]]:
    """Walk lines and yield (schema, [data_rows]) for each detected table.

    A table is: a header row whose cells match a known schema, immediately
    followed by a separator row, followed by data rows until a non-table line
    (empty or non-`|`-prefixed)."""
    tables: list[tuple[str, list[list[str]]]] = []
    i = 0
    while i < len(lines):
        cells = split_markdown_row(lines[i])
        if cells and not is_separator_row(cells):
            schema = detect_schema(cells)
            # peek at next line for separator
            if schema and i + 1 < len(lines):
                sep_cells = split_markdown_row(lines[i + 1])
                if is_separator_row(sep_cells):
                    rows: list[list[str]] = []
                    j = i + 2
                    while j < len(lines):
                        row_cells = split_markdown_row(lines[j])
                        if not row_cells or is_separator_row(row_cells):
                            break
                        rows.append(row_cells)
                        j += 1
                    tables.append((schema, rows))
                    i = j
                    continue
        i += 1
    return tables


def extract_intro_rows(
    schema: str, rows: list[list[str]], owner_label: str
) -> list[IntroRow]:
    """Project schema-specific rows into IntroRow, keeping only rows whose
    owner column equals owner_label (case-insensitive, trimmed)."""
    target = owner_label.strip().lower()
    out: list[IntroRow] = []
    for r in rows:
        if schema == "aylin":
            if len(r) < 4:
                continue
            company = r[0].strip()
            title = r[1].strip()
            owner = r[2].strip()
            reason = r[3].strip() or None
            if not company or owner.lower() != target:
                continue
            out.append(IntroRow(company=company, title=title, owner=owner, reason=reason))
        elif schema == "ylli":
            if len(r) < 7:
                continue
            company = r[0].strip()
            title = r[3].strip()
            owner = r[6].strip()
            # Why Meet? text lives in col 5 — keep as `reason` for richer logging.
            reason = r[5].strip() or None if len(r) > 5 else None
            if not company or owner.lower() != target:
                continue
            out.append(IntroRow(company=company, title=title, owner=owner, reason=reason))
    return out


# Strip the noisy company suffixes that prevent fuzzy matching from working
# well. Conservative — only well-known boilerplate.
_COMPANY_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|gmbh|sa|s\.a\.|sas|plc|corp|corporation|group|"
    r"holdings?|labs|capital|partners|the)\b\.?",
    re.IGNORECASE,
)


def normalize_company(s: str) -> str:
    """Lowercase, strip suffix noise, collapse whitespace + non-alphanum."""
    if not s:
        return ""
    x = s.lower()
    x = _COMPANY_NOISE.sub(" ", x)
    x = re.sub(r"[^a-z0-9]+", "", x)
    return x


def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def fuzzy_company_candidates(
    target_company: str,
    attendees: list,
    threshold: float = COMPANY_MATCH_THRESHOLD,
) -> list:
    """Return all attendees whose company fuzzy-matches target above threshold,
    sorted best-first. Exact-equal-after-normalize wins."""
    nt = normalize_company(target_company)
    if not nt:
        return []
    scored: list[tuple[float, object]] = []
    for a in attendees:
        nc = normalize_company(a.company or "")
        if not nc:
            continue
        if nc == nt:
            score = 1.0
        else:
            score = ratio(nc, nt)
        if score >= threshold:
            scored.append((score, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored]


def narrow_by_title(
    candidates: list, target_title: str, threshold: float = TITLE_MATCH_THRESHOLD
) -> object | None:
    """From multiple candidates at the same company, pick the one whose title
    best matches target_title. Returns None if no candidate clears threshold."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if not target_title:
        return candidates[0]  # fall back to best-by-company
    nt = target_title.lower().strip()
    # Title col on the sheet is often multi-value ("CEO, Co-Founder"); split
    # so each piece can match independently.
    title_parts = [p.strip() for p in nt.split(",") if p.strip()]
    best: tuple[float, object] | None = None
    for a in candidates:
        if not a.title:
            continue
        page_title = a.title.lower().strip()
        score = max(ratio(page_title, p) for p in title_parts)
        if best is None or score > best[0]:
            best = (score, a)
    if best is None or best[0] < threshold:
        return None
    return best[1]


def build_target_name_raw(title: str, company: str) -> str:
    """Sheet has no person name, so synthesise '{Title} at {Company}' for the
    target_name_raw field. Used both as a display string in the UI card and as
    part of the dedup key."""
    title = (title or "").strip() or "Unknown role"
    company = (company or "").strip() or "Unknown company"
    return f"{title} at {company}"


# ---------------------------------------------------------------------------
# Async DB work
# ---------------------------------------------------------------------------

async def _load_requester(db, email: str):
    result = await db.execute(
        select(Attendee).where(Attendee.email == email.strip().lower())
    )
    return result.scalars().first()


async def _load_attendees(db) -> list:
    """Pull every attendee with a non-null company. Filtering NULL company up
    front halves the in-memory list and skips the fuzzy normalize_company('')."""
    result = await db.execute(
        select(Attendee).where(Attendee.company.is_not(None))
    )
    return list(result.scalars().all())


async def _insert_intros(db, rows: list[dict]) -> int:
    """Upsert RequestedIntro rows. Returns inserted count.
    ON CONFLICT DO NOTHING on the dedup unique constraint."""
    if not rows:
        return 0
    stmt = (
        pg_insert(RequestedIntro)
        .values(rows)
        .on_conflict_do_nothing(
            constraint="uq_requested_intros_dedup",
        )
    )
    result = await db.execute(stmt)
    return result.rowcount or 0


def plan_intros(
    intro_rows: list[IntroRow],
    attendees: list,
    requester_id,
) -> tuple[list[dict], list[dict]]:
    """Pure orchestration: turn IntroRows + attendee pool into
    (rows_to_insert, miss_log). Each insert dict is shaped for RequestedIntro."""
    inserts: list[dict] = []
    misses: list[dict] = []
    for r in intro_rows:
        candidates = fuzzy_company_candidates(r.company, attendees)
        matched = narrow_by_title(candidates, r.title) if candidates else None
        inserts.append(
            {
                "requester_attendee_id": requester_id,
                "target_attendee_id": matched.id if matched else None,
                "target_name_raw": build_target_name_raw(r.title, r.company),
                "target_company_raw": r.company,
                "source": SOURCE_TAG,
            }
        )
        if not matched:
            misses.append(
                {
                    "company": r.company,
                    "title": r.title,
                    "candidate_count": len(candidates),
                    "candidate_names": [
                        f"{c.name} @ {c.company}" for c in candidates[:3]
                    ],
                }
            )
    return inserts, misses


async def main(args) -> int:
    text = Path(args.file).read_text()
    all_lines = text.splitlines()
    # Slice to the requested line range (1-indexed inclusive, matching the
    # digest's references). Falsy bounds = whole file.
    start = max(0, (args.start_line or 1) - 1)
    end = args.end_line if args.end_line else len(all_lines)
    lines = all_lines[start:end]

    tables = parse_tables(lines)
    if not tables:
        print(f"No markdown tables found in {args.file} lines {start+1}..{end}.")
        return 1

    intro_rows: list[IntroRow] = []
    for schema, rows in tables:
        intro_rows.extend(extract_intro_rows(schema, rows, args.owner_label))

    print(
        f"Parsed {len(tables)} table block(s); {len(intro_rows)} owner-matched "
        f"row(s) for label {args.owner_label!r}."
    )
    if not intro_rows:
        return 0

    async with async_session() as db:
        requester = await _load_requester(db, args.requester_email)
        if not requester:
            print(f"ERROR: requester email {args.requester_email!r} not in attendees.")
            return 2
        print(
            f"Requester: {requester.name} <{requester.email}> id={requester.id}"
        )

        attendees = await _load_attendees(db)
        print(f"Loaded {len(attendees)} attendees with a company set.")

        inserts, misses = plan_intros(intro_rows, attendees, requester.id)

        match_count = sum(1 for r in inserts if r["target_attendee_id"])
        miss_count = len(inserts) - match_count
        print(
            f"Plan: {match_count} matched to existing attendee, "
            f"{miss_count} unresolved (target_attendee_id=NULL)."
        )

        if misses:
            print("\nUnresolved rows (will surface as greyed-out cards):")
            for m in misses:
                cand = (
                    f" — {m['candidate_count']} weak candidate(s): {m['candidate_names']}"
                    if m["candidate_count"]
                    else ""
                )
                print(f"  - {m['title']} at {m['company']}{cand}")

        if not args.confirm:
            print("\nDry run. Re-run with --confirm to insert.")
            return 0

        inserted = await _insert_intros(db, inserts)
        await db.commit()
        print(
            f"\nInserted {inserted} new RequestedIntro row(s) "
            f"({len(inserts) - inserted} already existed)."
        )
        return 0


def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--file", required=True, help="Markdown sheet export.")
    p.add_argument(
        "--requester-email", required=True,
        help="Elliptic person whose tab this is (must exist in attendees).",
    )
    p.add_argument(
        "--owner-label", required=True,
        help="Exact owner string in the sheet (e.g. 'Aylin Zanier' or 'Ylli').",
    )
    p.add_argument(
        "--start-line", type=int, default=None,
        help="1-indexed start line of the section to ingest.",
    )
    p.add_argument(
        "--end-line", type=int, default=None,
        help="1-indexed end line (inclusive) of the section.",
    )
    p.add_argument("--confirm", action="store_true", help="Commit inserts.")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(main(_cli())))
