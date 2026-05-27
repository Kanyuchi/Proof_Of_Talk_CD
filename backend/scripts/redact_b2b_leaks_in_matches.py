"""Scan every Match row involving a b2b_only attendee and mask leaked
real names from the stored explanation + shared_context fields.

Why: the LLM-side b2b mask shipped 2026-05-27 (commits 6965805 + 9e6ccbe
+ 01b1457) prevents NEW leaks, but historical rows written before those
commits still carry pre-fix explanation text. The daily 03:30 UTC cron
calls `refresh_matches_for_new_attendees` which only processes attendees
with zero matches yet, so existing Match rows never auto-refresh. This
script is the one-off cleanup.

Behaviour: dry-run by default. Prints a per-match before/after diff for
the first 5 changes, then a summary. Pass --confirm to commit. Idempotent
- a second run finds zero new changes once committed.

    python scripts/redact_b2b_leaks_in_matches.py
    python scripts/redact_b2b_leaks_in_matches.py --confirm
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, or_  # noqa: E402
from sqlalchemy.orm.attributes import flag_modified  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.models.attendee import Attendee, Match  # noqa: E402
from app.services.b2b_match_redact import redact_b2b_in_match_fields  # noqa: E402


async def main(confirm: bool, preview_limit: int) -> None:
    async with async_session() as db:
        # Find every Match where at least one side is privacy_mode='b2b_only'.
        # DISTINCT collapses the duplicate rows the OR-join produces when
        # BOTH sides are b2b.
        result = await db.execute(
            select(Match)
            .join(
                Attendee,
                or_(
                    Attendee.id == Match.attendee_a_id,
                    Attendee.id == Match.attendee_b_id,
                ),
            )
            .where(Attendee.privacy_mode == "b2b_only")
            .distinct()
        )
        matches = result.scalars().unique().all()

        scanned = 0
        changed = 0
        previews_shown = 0

        for match in matches:
            scanned += 1
            attendee_a = await db.get(Attendee, match.attendee_a_id)
            attendee_b = await db.get(Attendee, match.attendee_b_id)

            current_explanation = match.explanation
            current_context = match.shared_context
            this_row_changed = False

            # If both sides are b2b, run the mask for each in turn so both
            # real names are redacted.
            for side in (attendee_a, attendee_b):
                if side is None or getattr(side, "privacy_mode", "full") != "b2b_only":
                    continue
                fields = redact_b2b_in_match_fields(
                    current_explanation, current_context, side,
                )
                if "explanation" in fields:
                    current_explanation = fields["explanation"]
                    this_row_changed = True
                if "shared_context" in fields:
                    current_context = fields["shared_context"]
                    this_row_changed = True

            if not this_row_changed:
                continue

            changed += 1

            if previews_shown < preview_limit:
                previews_shown += 1
                b2b_side = attendee_a if getattr(attendee_a, "privacy_mode", "full") == "b2b_only" else attendee_b
                print(
                    f"\n=== Match {match.id} "
                    f"(b2b: {b2b_side.company!r} / real: {b2b_side.name!r}) ==="
                )
                if current_explanation != match.explanation:
                    before = (match.explanation or "")[:200]
                    after = (current_explanation or "")[:200]
                    print(f"  EXPLANATION BEFORE: {before}")
                    print(f"  EXPLANATION AFTER:  {after}")
                if current_context != match.shared_context:
                    print("  CONTEXT changed (synergies / action_items / sectors)")

            if confirm:
                if current_explanation != match.explanation:
                    match.explanation = current_explanation
                if current_context != match.shared_context:
                    match.shared_context = current_context
                    # JSONB column - SQLAlchemy needs the explicit flag to
                    # notice nested-dict mutation.
                    flag_modified(match, "shared_context")
                db.add(match)

        if confirm:
            await db.commit()
            print(f"\nCommitted {changed} updates ({scanned} b2b matches scanned).")
        else:
            print(
                f"\nDRY-RUN: {changed} updates would be made "
                f"({scanned} b2b matches scanned).\n"
                f"Re-run with --confirm to commit."
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--confirm", action="store_true",
        help="Commit changes (default is dry-run preview only).",
    )
    parser.add_argument(
        "--preview-limit", type=int, default=5,
        help="How many per-row before/after diffs to print (default 5).",
    )
    args = parser.parse_args()
    asyncio.run(main(args.confirm, args.preview_limit))
