"""
Triage unmatched domains from the latest Grid audit
====================================================
For each domain that didn't resolve to a Grid profile, classify how
likely the company *should* be on The Grid, based on the enrichment
data we already have on its attendees:

- HIGH:  clearly Web3-native (product is a chain, protocol, DeFi app,
        custody, wallet, exchange, etc.). These are the ones to flag
        to the Grid team for inclusion.
- MED:   Web3-adjacent (traditional firm with active Web3 practice or
        product line — judgment call).
- LOW:   no Web3 signal in the enrichment we have (traditional finance,
        legal, academic, generic services).

Output: a markdown report at backend/exports/grid_unmatched_triage.md
plus a CSV at backend/exports/grid_unmatched_triage.csv for the team.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/grid_unmatched_triage.py
"""

import asyncio
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from app.services.grid_audit import last_audit  # noqa: E402

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Strong Web3 signal terms — presence in description/summary → HIGH
HIGH_SIGNALS = {
    "blockchain", "web3", "crypto", "defi", "nft", "dao", "tokenis", "tokeniz",
    "stablecoin", "smart contract", "layer 2", "l2", "rollup", "zk-",
    "depin", "wallet", "custody", "validator", "staking", "bridge protocol",
    "dex ", "exchange", "on-chain", "onchain", "ethereum", "bitcoin",
    "solana", "polygon", "cosmos", "polkadot", "avalanche", "near protocol",
    "decentralized", "decentralised", "rwa", "real-world asset",
    "metaverse", "game-fi", "gamefi", "play-to-earn", "p2e",
}

# Mid signals — Web3 client / advisory / fund context, not necessarily Web3-native
MID_SIGNALS = {
    "digital asset", "digital assets", "fintech", "private bank", "asset management",
    "venture capital", "vc fund", "investment fund", "family office",
    "advisory", "consulting", "law firm", "compliance",
}

# Domains we know shouldn't be on Grid (academic, government, generic platforms)
EXPLICIT_LOW = {
    "kcl.ac.uk", "google.com", "iheartmedia.com", "speaker.proofoftalk.io",
}


def sb_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }


def fetch_attendees_by_domains(domains: list[str]) -> dict[str, list[dict]]:
    """Fetch all attendees on the given domains, grouped by domain.

    Uses one query per domain (REST `ilike` doesn't combine cleanly with
    `in.()`). 59 domains × ~50ms each = ~3s, fine for a one-off triage.
    """
    by_domain: dict[str, list[dict]] = defaultdict(list)
    with httpx.Client(timeout=30) as client:
        for d in domains:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/attendees",
                headers=sb_headers(),
                params={
                    "select": "name,email,company,title,goals,enriched_profile,ai_summary,vertical_tags",
                    "email": f"ilike.*@{d}",
                },
            )
            resp.raise_for_status()
            by_domain[d].extend(resp.json())
    return by_domain


def _signal_text(attendee: dict) -> str:
    """Concatenate all enrichment text we'll inspect for Web3 signals."""
    bits: list[str] = [
        attendee.get("company") or "",
        attendee.get("title") or "",
        attendee.get("goals") or "",
        attendee.get("ai_summary") or "",
    ]
    enriched = attendee.get("enriched_profile") or {}
    for key in ("company_description", "linkedin_summary", "website"):
        v = enriched.get(key)
        if isinstance(v, str):
            bits.append(v)
    li = enriched.get("linkedin") or {}
    if isinstance(li, dict):
        bits.append(li.get("headline") or "")
        bits.append(li.get("summary") or "")
    return " ".join(bits).lower()


def _vertical_tag_signal(attendees: list[dict]) -> tuple[bool, list[str]]:
    """Web3-y vertical tags raise the score even without keyword hits."""
    web3_verticals = {
        "infrastructure_and_scaling", "decentralized_finance", "tokenisation_of_finance",
        "decentralized_ai", "ai_depin_frontier_tech", "ecosystem_and_foundations",
        "culture_media_gaming",  # often NFT/gaming Web3
    }
    found_tags: set[str] = set()
    for a in attendees:
        for t in a.get("vertical_tags") or []:
            if t in web3_verticals:
                found_tags.add(t)
    return bool(found_tags), sorted(found_tags)


def classify(domain: str, attendees: list[dict]) -> dict:
    """Return classification + reasoning for this domain."""
    if domain in EXPLICIT_LOW:
        return {
            "classification": "LOW",
            "reason": "Generic platform / academic / non-company domain",
            "signals": [],
            "verticals": [],
            "company": "",
            "n_attendees": len(attendees),
        }

    n = len(attendees)
    if n == 0:
        return {
            "classification": "LOW",
            "reason": "No attendees found on this domain (stale audit?)",
            "signals": [], "verticals": [], "company": "", "n_attendees": 0,
        }

    text = " ".join(_signal_text(a) for a in attendees)
    high_hits = sorted({s for s in HIGH_SIGNALS if s in text})
    mid_hits = sorted({s for s in MID_SIGNALS if s in text})

    has_web3_vertical, verticals = _vertical_tag_signal(attendees)

    company = next((a.get("company") for a in attendees if a.get("company")), "") or ""

    if high_hits:
        return {
            "classification": "HIGH",
            "reason": f"Web3-native signals: {', '.join(high_hits[:5])}",
            "signals": high_hits,
            "verticals": verticals,
            "company": company,
            "n_attendees": n,
        }
    if has_web3_vertical and mid_hits:
        return {
            "classification": "MED",
            "reason": f"Web3-adjacent: vertical {','.join(verticals)} + {', '.join(mid_hits[:3])}",
            "signals": mid_hits,
            "verticals": verticals,
            "company": company,
            "n_attendees": n,
        }
    if has_web3_vertical:
        return {
            "classification": "MED",
            "reason": f"Web3 vertical tag ({','.join(verticals)}) but no descriptive Web3 keywords",
            "signals": [], "verticals": verticals, "company": company, "n_attendees": n,
        }
    if mid_hits:
        return {
            "classification": "LOW",
            "reason": f"Traditional firm with possible Web3 interest ({', '.join(mid_hits[:3])})",
            "signals": mid_hits, "verticals": [], "company": company, "n_attendees": n,
        }
    return {
        "classification": "LOW",
        "reason": "No Web3 signals found in available enrichment",
        "signals": [], "verticals": [], "company": company, "n_attendees": n,
    }


def write_outputs(rows: list[dict]) -> None:
    out_md = ROOT / "exports" / "grid_unmatched_triage.md"
    out_csv = ROOT / "exports" / "grid_unmatched_triage.csv"

    by_class: dict[str, list[dict]] = {"HIGH": [], "MED": [], "LOW": []}
    for r in rows:
        by_class[r["classification"]].append(r)

    with open(out_md, "w") as f:
        f.write("# Grid Unmatched Domain Triage\n\n")
        f.write(f"Source: latest grid_audit_runs row. {len(rows)} unmatched domains audited.\n\n")
        f.write(f"- **HIGH** ({len(by_class['HIGH'])}) — Web3-native; flag to the Grid team for inclusion.\n")
        f.write(f"- **MED** ({len(by_class['MED'])}) — Web3-adjacent; judgment call.\n")
        f.write(f"- **LOW** ({len(by_class['LOW'])}) — Traditional / non-Web3; expected absence.\n\n")
        for tier in ("HIGH", "MED", "LOW"):
            f.write(f"## {tier}\n\n")
            for r in by_class[tier]:
                f.write(f"### `{r['domain']}` — {r['company'] or '(unknown)'} ({r['n_attendees']} attendee{'s' if r['n_attendees']!=1 else ''})\n")
                f.write(f"- **Why:** {r['reason']}\n")
                if r["signals"]:
                    f.write(f"- **Signals:** {', '.join(r['signals'])}\n")
                if r["verticals"]:
                    f.write(f"- **Verticals:** {', '.join(r['verticals'])}\n")
                f.write("\n")

    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "domain", "company", "classification", "reason", "n_attendees", "signals", "verticals",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "domain": r["domain"],
                "company": r["company"],
                "classification": r["classification"],
                "reason": r["reason"],
                "n_attendees": r["n_attendees"],
                "signals": ";".join(r["signals"]),
                "verticals": ";".join(r["verticals"]),
            })

    print(f"\nWrote: {out_md}")
    print(f"Wrote: {out_csv}")


async def main() -> None:
    last = await last_audit()
    if not last:
        print("No grid_audit_runs row found — run the audit first.")
        sys.exit(1)
    domains = last["unmatched_domains"]
    print(f"Latest audit: {last['run_at']}, {len(domains)} unmatched domains.\n")

    by_domain = fetch_attendees_by_domains(domains)
    rows = []
    for d in domains:
        classification = classify(d, by_domain.get(d, []))
        rows.append({"domain": d, **classification})

    rows.sort(key=lambda r: (
        {"HIGH": 0, "MED": 1, "LOW": 2}[r["classification"]],
        -r["n_attendees"],
        r["domain"],
    ))

    counts = {c: sum(1 for r in rows if r["classification"] == c) for c in ("HIGH", "MED", "LOW")}
    print("--- Summary ---")
    print(f"  HIGH (flag to Grid team): {counts['HIGH']}")
    print(f"  MED  (judgment call):     {counts['MED']}")
    print(f"  LOW  (expected absence):  {counts['LOW']}")
    print()

    print("--- HIGH (flag to Grid team) ---")
    for r in rows:
        if r["classification"] != "HIGH":
            continue
        print(f"  {r['domain']:35s} {r['company']:35s} ({r['n_attendees']}) — {r['reason']}")

    print("\n--- MED (judgment call) ---")
    for r in rows:
        if r["classification"] != "MED":
            continue
        print(f"  {r['domain']:35s} {r['company']:35s} ({r['n_attendees']}) — {r['reason']}")

    write_outputs(rows)


if __name__ == "__main__":
    asyncio.run(main())
