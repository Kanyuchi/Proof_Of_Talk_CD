"""
Refresh AI summary + intent tags + embedding for profiles whose LinkedIn data
was scraped on or after a cutoff date. The Playwright script only patches
enriched_profile.linkedin — it does NOT touch ai_summary or the embedding,
so the newly-scraped LinkedIn data isn't reflected in matching until this
script runs.
"""
from __future__ import annotations
import asyncio, os, sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
sys.path.insert(0, str(Path(__file__).parent))
from enrich_and_embed import (  # noqa: E402
    sb_headers, patch_attendee, generate_ai_summary, classify_intents,
    generate_embedding, build_composite_text,
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
# 2026-05-15: refreshing ALL LinkedIn-enriched profiles after we rewrote the
# generate_ai_summary prompt to surface LinkedIn About content (Chiara, Joris
# regression — old summaries were generic stubs that ignored rich LinkedIn data).
CUTOFF = "2024-01-01"


def fetch_targets() -> list[dict]:
    with httpx.Client(timeout=30) as c:
        resp = c.get(
            f"{SUPABASE_URL}/rest/v1/attendees",
            headers=sb_headers(),
            params={
                "select": "id,name,email,company,title,ticket_type,goals,interests,"
                          "linkedin_url,company_website,enriched_profile,ai_summary,"
                          "intent_tags,embedding",
                "enriched_profile->>linkedin_enriched_at": f"gte.{CUTOFF}",
                "order": "name.asc",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh(att: dict) -> str:
    summary = await generate_ai_summary(att)
    tags = await classify_intents(att)
    deal = {"deploying_capital", "raising_capital", "deal_making", "seeking_customers"}
    score = len(set(tags) & deal) / len(deal)
    composite = build_composite_text({**att, "ai_summary": summary})
    embedding = await generate_embedding(composite)
    patch = {
        "ai_summary": summary,
        "intent_tags": tags,
        "deal_readiness_score": score,
        "embedding": "[" + ",".join(str(v) for v in embedding) + "]",
    }
    ok = patch_attendee(att["id"], patch, dry_run=False)
    return f"{att['name']}: tags={tags} patch={'ok' if ok else 'ERR'}"


async def main():
    targets = fetch_targets()
    print(f"Refreshing {len(targets)} profiles with new LinkedIn data\n")
    ok = err = 0
    for i, a in enumerate(targets, 1):
        try:
            r = await refresh(a)
            print(f"  [{i:>3}/{len(targets)}] {r}")
            ok += 1
        except Exception as exc:
            print(f"  [{i:>3}/{len(targets)}] ERR {a.get('name')}: {exc}")
            err += 1
    print(f"\nDone: {ok} ok, {err} errors")


if __name__ == "__main__":
    asyncio.run(main())
