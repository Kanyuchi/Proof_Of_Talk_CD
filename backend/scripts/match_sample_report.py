"""
Match Sample Report
====================
Pulls a representative spread of matches across the score range and writes
a human-readable Markdown report showing:
  - Who is matched with whom
  - The match type (deal_ready / non_obvious / complementary)
  - The overall score + component scores (similarity / complementary)
  - GPT-4o's explanation for why they should meet
  - Shared context (overlapping interests / sectors)

Useful for sanity-checking the AI matching engine — especially for
demo reviews (Zohair's question: "show me some high and low matches
and why they were matched").

Usage:
    cd backend && source .venv/bin/activate
    python scripts/match_sample_report.py                   # markdown to stdout
    python scripts/match_sample_report.py --out report.md   # write to file
    python scripts/match_sample_report.py --per-bucket 5    # 5 matches per bucket
"""

import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    sys.exit(1)

# Internal staff exclusion. Anyone at @xventures.de or @proofoftalk.io is
# considered organiser staff and is excluded from the matching pool, with the
# SOLE EXCEPTION of Zohair and Victor — both are X Ventures partners who use
# the matching as any external VC would.
INTERNAL_EMAIL_DOMAINS = {"proofoftalk.io", "xventures.de", "x-ventures.de"}
INTERNAL_COMPANY_PATTERNS = {
    "proof of talk", "proofoftalk", "proof of talk sa",
    "xventures", "x ventures", "x-ventures", "xventures labs",
}

# Allow-list: ONLY Zohair and Victor are kept despite being at xventures.de.
ALLOWED_NAMES = {
    "zohair dehnadi",
    "victor blas",
}


def is_internal(attendee: dict) -> bool:
    """Return True if this attendee is POT/X Ventures organiser staff.

    Exception: Zohair and Victor (ALLOWED_NAMES) are always kept — they use
    the matchmaker as external VCs would.
    """
    name = (attendee.get("name") or "").strip().lower()
    if name in ALLOWED_NAMES:
        return False

    email = (attendee.get("email") or "").lower()
    if "@" in email:
        domain = email.split("@", 1)[1]
        # @speaker.proofoftalk.io is OK (legitimate external speakers)
        if domain in INTERNAL_EMAIL_DOMAINS:
            return True

    company = (attendee.get("company") or "").strip().lower()
    if company in INTERNAL_COMPANY_PATTERNS:
        return True

    return False


def sb_headers():
    return {"apikey": SUPABASE_SERVICE_ROLE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"}


def fetch_attendees() -> dict[str, dict]:
    """Return {attendee_id: attendee_dict}."""
    resp = httpx.get(f"{SUPABASE_URL}/rest/v1/attendees",
        headers=sb_headers(),
        params={"select": "id,name,email,company,title,ticket_type,goals,vertical_tags,intent_tags,ai_summary,enriched_profile", "limit": 500},
        timeout=30)
    resp.raise_for_status()
    return {a["id"]: a for a in resp.json()}


def fetch_matches(limit: int = 500) -> list[dict]:
    resp = httpx.get(f"{SUPABASE_URL}/rest/v1/matches",
        headers=sb_headers(),
        params={"select": "*", "order": "overall_score.desc", "limit": str(limit)},
        timeout=30)
    resp.raise_for_status()
    return resp.json()


def pick_sample(matches: list[dict], per_bucket: int) -> list[tuple[str, list[dict]]]:
    """Split matches into buckets and pick per_bucket from each."""
    buckets = {
        "Top matches (≥0.75)":       [m for m in matches if m["overall_score"] >= 0.75],
        "High (0.70–0.75)":          [m for m in matches if 0.70 <= m["overall_score"] < 0.75],
        "Medium (0.65–0.70)":        [m for m in matches if 0.65 <= m["overall_score"] < 0.70],
        "Borderline (0.60–0.65)":    [m for m in matches if 0.60 <= m["overall_score"] < 0.65],
    }
    # Also bucket by type so we get at least one of each
    type_buckets: dict[str, list[dict]] = {}
    for m in matches:
        type_buckets.setdefault(m.get("match_type", "unknown"), []).append(m)

    picks = []
    for label, bucket in buckets.items():
        # Pick a spread across match types within each score bucket
        seen_ids = set()
        sample = []
        by_type: dict[str, list[dict]] = {}
        for m in bucket:
            by_type.setdefault(m.get("match_type", "unknown"), []).append(m)
        # Take 1-2 from each type, up to per_bucket total
        for mtype, items in by_type.items():
            for m in items[: max(1, per_bucket // max(1, len(by_type)))]:
                if m["id"] not in seen_ids:
                    sample.append(m)
                    seen_ids.add(m["id"])
                if len(sample) >= per_bucket:
                    break
            if len(sample) >= per_bucket:
                break
        picks.append((label, sample[:per_bucket]))
    return picks


def format_attendee(a: dict) -> str:
    bits = [f"**{a.get('name', '?')}**"]
    title = a.get("title") or ""
    company = a.get("company") or ""
    if title or company:
        bits.append(f"{title}{' at ' if title and company else ''}{company}".strip())
    ticket = a.get("ticket_type") or ""
    if ticket:
        bits.append(f"[{ticket}]")
    return " — ".join(bits)


def format_context(a: dict) -> list[str]:
    """Short bullets with verticals / intents / goals / LinkedIn headline."""
    bullets = []
    verticals = a.get("vertical_tags") or []
    if verticals:
        bullets.append(f"Sectors: {', '.join(verticals[:5])}")
    intents = a.get("intent_tags") or []
    if intents:
        bullets.append(f"Intents: {', '.join(intents[:4])}")
    goals = a.get("goals") or ""
    if goals:
        g = goals[:180] + ("…" if len(goals) > 180 else "")
        bullets.append(f"Goals: {g}")
    ep = a.get("enriched_profile") or {}
    ln = ep.get("linkedin") or {}
    if ln.get("headline"):
        h = ln["headline"][:150] + ("…" if len(ln["headline"]) > 150 else "")
        bullets.append(f"LinkedIn: {h}")
    grid = ep.get("grid") or {}
    if grid.get("grid_description"):
        g = grid["grid_description"][:200] + ("…" if len(grid["grid_description"]) > 200 else "")
        bullets.append(f"Grid: {g}")
    return bullets


def format_match_markdown(m: dict, attendees: dict[str, dict]) -> str:
    a = attendees.get(m["attendee_a_id"])
    b = attendees.get(m["attendee_b_id"])
    if not a or not b:
        return ""

    lines = []
    score = m.get("overall_score", 0)
    sim = m.get("similarity_score", 0) or 0
    comp = m.get("complementary_score", 0) or 0
    mtype = m.get("match_type", "?")
    mtype_emoji = {"deal_ready": "💼", "non_obvious": "✨", "complementary": "🤝"}.get(mtype, "•")

    lines.append(f"### {mtype_emoji} {a['name']}  ↔  {b['name']}")
    lines.append(f"**Overall score: {score:.2f}**  |  Match type: `{mtype}`  |  Embedding similarity: {sim:.2f}  |  Complementary: {comp:.2f}")
    lines.append("")
    lines.append(f"- {format_attendee(a)}")
    for ctx in format_context(a):
        lines.append(f"  - {ctx}")
    lines.append(f"- {format_attendee(b)}")
    for ctx in format_context(b):
        lines.append(f"  - {ctx}")
    lines.append("")

    explanation = (m.get("explanation") or "").strip()
    if explanation:
        lines.append(f"**Why they should meet (GPT-4o):**")
        lines.append(f"> {explanation}")
    else:
        lines.append(f"_No explanation stored._")

    shared = m.get("shared_context")
    if shared:
        lines.append("")
        if isinstance(shared, dict):
            shared_bits = []
            for k, v in shared.items():
                if isinstance(v, list) and v:
                    shared_bits.append(f"{k}: {', '.join(str(x) for x in v)}")
                elif isinstance(v, str) and v:
                    shared_bits.append(f"{k}: {v}")
                elif v:
                    shared_bits.append(f"{k}: {v}")
            if shared_bits:
                lines.append(f"**Shared context:** {' | '.join(shared_bits)}")
        else:
            lines.append(f"**Shared context:** {shared}")

    confidence = m.get("explanation_confidence")
    if confidence is not None:
        lines.append("")
        lines.append(f"_Explanation confidence: {confidence:.2f}_")
    lines.append("")
    return "\n".join(lines)


def main(out_path: str | None, per_bucket: int):
    print("Fetching matches + attendees from Supabase...", file=sys.stderr)
    attendees = fetch_attendees()
    matches = fetch_matches()
    print(f"  {len(attendees)} attendees, {len(matches)} matches", file=sys.stderr)

    # Exclude matches where either side is POT / X Ventures internal staff
    internal_ids = {aid for aid, a in attendees.items() if is_internal(a)}
    internal_names = sorted({attendees[i].get("name", "?") for i in internal_ids})
    print(f"  Excluding {len(internal_ids)} internal staff: {', '.join(internal_names)}", file=sys.stderr)
    before = len(matches)
    matches = [
        m for m in matches
        if m.get("attendee_a_id") not in internal_ids
        and m.get("attendee_b_id") not in internal_ids
    ]
    print(f"  Matches after exclusion: {len(matches)} (removed {before - len(matches)})", file=sys.stderr)

    buckets = pick_sample(matches, per_bucket)

    lines = []
    lines.append("# POT Matchmaker — Sample Match Report")
    lines.append("")
    scores = [m["overall_score"] for m in matches]
    external_count = len(attendees) - len(internal_ids)
    lines.append(f"**Generated from {len(matches)} matches across {external_count} attendees.**")
    lines.append(f"_Proof of Talk + X Ventures organiser staff ({len(internal_ids)}) excluded from this report. "
                 f"Zohair Dehnadi and Victor Blas are kept as they use the matchmaker like any other VC._")
    lines.append(f"Score range: {min(scores):.3f} → {max(scores):.3f}, mean {sum(scores)/len(scores):.3f}.")
    lines.append("")
    lines.append("## How scoring works")
    lines.append("")
    lines.append("Each match has three scores:")
    lines.append("- **Embedding similarity** — cosine similarity of the two attendees' profile embeddings (text-embedding-3-small, 1536-dim). Pure semantic overlap.")
    lines.append("- **Complementary score** — deterministic rerank based on sector pairing, intent alignment, and ICP signal-keyword overlap (does A offer what B is seeking?).")
    lines.append("- **Overall score** — the final score used for ranking. Combines similarity + complementary signals.")
    lines.append("")
    lines.append("Match types:")
    lines.append("- 💼 `deal_ready` — both parties in a position to transact (investor + startup, buyer + seller).")
    lines.append("- ✨ `non_obvious` — different sectors solving the same underlying problem.")
    lines.append("- 🤝 `complementary` — one party has what the other needs.")
    lines.append("")

    for label, sample in buckets:
        lines.append(f"## {label}")
        lines.append("")
        if not sample:
            lines.append("_None in this score bucket._")
            lines.append("")
            continue
        for m in sample:
            block = format_match_markdown(m, attendees)
            if block:
                lines.append(block)
                lines.append("---")
                lines.append("")

    report = "\n".join(lines)

    if out_path:
        Path(out_path).write_text(report)
        print(f"Report written to: {out_path}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Output file (default: stdout)")
    parser.add_argument("--per-bucket", type=int, default=3, help="Matches per score bucket (default: 3)")
    args = parser.parse_args()
    main(args.out, args.per_bucket)
