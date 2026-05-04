"""
Targeted enrichment for newly-ingested speakers.
Only processes attendees where enriched_profile.source = 'speakers_sheet'
and ai_summary IS NULL. Reuses helpers from enrich_and_embed.py.

Skips LinkedIn (manual Playwright path) and skips full website scrape —
just generates AI summary + intent tags + embedding from sheet data
(name, title, company, bio).

Usage:
    cd backend && source .venv/bin/activate
    python scripts/enrich_speakers_only.py
    python scripts/enrich_speakers_only.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from enrich_and_embed import (  # noqa: E402
    sb_headers,
    patch_attendee,
    generate_ai_summary,
    classify_intents,
    generate_embedding,
    build_composite_text,
)

SUPABASE_URL = os.getenv("SUPABASE_URL")


def fetch_pending_speakers() -> list[dict]:
    """Fetch speaker_sheet rows that still need AI summary + embedding."""
    url = f"{SUPABASE_URL}/rest/v1/attendees"
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            url,
            headers=sb_headers(),
            params={
                "select": "id,name,email,company,title,ticket_type,goals,interests,"
                          "linkedin_url,company_website,enriched_profile,ai_summary,"
                          "intent_tags,embedding",
                "ai_summary": "is.null",
                "enriched_profile->>source": "eq.speakers_sheet",
                "order": "name.asc",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def enrich_one(attendee: dict, dry_run: bool) -> str:
    """AI summary + intent tags + embedding only. No website / Grid here."""
    name = attendee.get("name", "Unknown")
    aid = attendee["id"]

    summary = await generate_ai_summary(attendee)
    tags = await classify_intents(attendee)
    deal_signals = {"deploying_capital", "raising_capital", "deal_making", "seeking_customers"}
    deal_score = len(set(tags) & deal_signals) / len(deal_signals)

    attendee_for_embed = {**attendee, "ai_summary": summary}
    composite = build_composite_text(attendee_for_embed)
    embedding = await generate_embedding(composite)
    embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

    patch = {
        "ai_summary": summary,
        "intent_tags": tags,
        "deal_readiness_score": deal_score,
        "embedding": embedding_str,
    }

    if dry_run:
        return f"DRY {name}: summary[{len(summary)}c] tags[{len(tags)}] embed[{len(embedding)}d] deal={deal_score:.2f}"

    ok = patch_attendee(aid, patch, dry_run=False)
    return f"{name}: tags={tags} deal={deal_score:.2f} patch={'ok' if ok else 'ERR'}"


async def main(dry_run: bool) -> None:
    print("=== Targeted speaker enrichment (sheet → AI summary + embedding) ===\n")
    pending = fetch_pending_speakers()
    print(f"Pending: {len(pending)} speakers\n")

    ok = err = 0
    for i, sp in enumerate(pending, 1):
        try:
            result = await enrich_one(sp, dry_run=dry_run)
            print(f"  [{i:>3}/{len(pending)}] {result}")
            ok += 1
        except Exception as exc:
            print(f"  [{i:>3}/{len(pending)}] ERR {sp.get('name')}: {exc}")
            err += 1

    print(f"\nDone: {ok} ok, {err} errors / {len(pending)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
