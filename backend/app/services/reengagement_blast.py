"""Re-engagement blast: cohort query + per-recipient context + subject picker.

Targets attendees who have a magic token but no `users` row
(`has_account=false`). Personalisation per recipient is the total
curated+priority_intro+similar match count and the count of OTHER
attendees who have already marked them as a match interest.

Spec:  docs/superpowers/specs/2026-05-31-reengagement-blast-design.md
Plan:  docs/superpowers/plans/2026-05-31-reengagement-blast-plan.md
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class RecipientContext:
    attendee_id: str
    email: str
    first_name: str
    magic_token: str
    total_matches: int
    incoming_interest_count: int
    top_matches: list[dict]


def pick_subject(
    *,
    first_name: str,
    total_matches: int,
    incoming_interest_count: int,
) -> str | None:
    """Return the subject line for this recipient, or None if no honest hook.

    Rules:
      total_matches == 0          -> None  (caller skips the send)
      incoming_interest_count > 0 -> reciprocity hook (strongest)
      else                        -> concrete count + venue/day anchor
    """
    if total_matches == 0:
        return None
    if incoming_interest_count == 1:
        return "1 person wants to meet you at Proof of Talk"
    if incoming_interest_count > 1:
        return f"{incoming_interest_count} people want to meet you at Proof of Talk"
    return f"Your {total_matches} matches at the Louvre, this Tuesday"


COHORT_SQL = text("""
SELECT
  a.id,
  a.email,
  a.name,
  a.magic_access_token,
  (
    SELECT COUNT(*) FROM matches m
    WHERE (m.attendee_a_id = a.id OR m.attendee_b_id = a.id)
      AND m.tier IN ('curated', 'priority_intro', 'similar')
  ) AS total_matches,
  (
    SELECT COUNT(*) FROM matches m
    WHERE (
      (m.attendee_a_id = a.id AND m.status_b = 'accepted')
      OR (m.attendee_b_id = a.id AND m.status_a = 'accepted')
    )
  ) AS incoming_interest_count
FROM attendees a
LEFT JOIN users u ON u.attendee_id = a.id
WHERE u.id IS NULL
  AND a.email_opt_out IS NOT TRUE
  AND a.matching_consent != 'pending'
  AND a.magic_access_token IS NOT NULL
  AND a.email NOT LIKE '%@demo.proofoftalk.io'
  AND a.email NOT LIKE '%@speaker.proofoftalk.io'
ORDER BY a.email
""")


TOP_MATCHES_SQL = text("""
SELECT
  CASE WHEN m.attendee_a_id = :aid THEN m.attendee_b_id ELSE m.attendee_a_id END AS other_id,
  m.overall_score
FROM matches m
WHERE (m.attendee_a_id = :aid OR m.attendee_b_id = :aid)
  AND m.tier IN ('curated', 'priority_intro')
ORDER BY m.overall_score DESC NULLS LAST
LIMIT 2
""")


OTHER_ATTENDEE_SQL = text("""
SELECT id, name, title, company, privacy_mode
FROM attendees
WHERE id = ANY(:ids)
""")


async def build_cohort(db: AsyncSession) -> list[RecipientContext]:
    """Return one row per targetable unregistered attendee with match counts.

    Top-matches stay empty here; the caller fills them per-recipient via
    `fill_top_matches()` so the bulk cohort assembly stays a single query.
    """
    rows = (await db.execute(COHORT_SQL)).mappings().all()
    out: list[RecipientContext] = []
    for r in rows:
        name = (r["name"] or "").strip()
        first_name = name.split()[0] if name else r["email"].split("@")[0]
        out.append(
            RecipientContext(
                attendee_id=str(r["id"]),
                email=r["email"],
                first_name=first_name,
                magic_token=r["magic_access_token"],
                total_matches=int(r["total_matches"]),
                incoming_interest_count=int(r["incoming_interest_count"]),
                top_matches=[],
            )
        )
    return out


async def fill_top_matches(db: AsyncSession, ctx: RecipientContext) -> None:
    """Hydrate ctx.top_matches with up to 2 dicts {name, title, company}.

    Privacy: b2b_only counterparts surface as company-name + blank title,
    matching the convention used by send_t_minus_one_reminder_email.
    """
    rows = (await db.execute(TOP_MATCHES_SQL, {"aid": ctx.attendee_id})).mappings().all()
    if not rows:
        return
    other_ids = [str(r["other_id"]) for r in rows]
    by_id = {
        str(r["id"]): r for r in
        (await db.execute(OTHER_ATTENDEE_SQL, {"ids": other_ids})).mappings().all()
    }
    out: list[dict] = []
    for r in rows:
        other = by_id.get(str(r["other_id"]))
        if not other:
            continue
        if other["privacy_mode"] == "b2b_only":
            name = (other["company"] or "Anonymous").strip()
            title = ""
        else:
            name = (other["name"] or "").strip()
            title = (other["title"] or "").strip()
        out.append(
            {
                "name": name,
                "title": title,
                "company": (other["company"] or "").strip(),
            }
        )
    ctx.top_matches = out
