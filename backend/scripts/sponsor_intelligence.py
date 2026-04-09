"""
Sponsor Intelligence Report Generator
======================================
Generates personalised intelligence reports for POT 2026 sponsors.
For each sponsor company, queries The Grid for verified data, embeds
the company profile, finds the most relevant attendees via pgvector,
and uses GPT-4o to explain why each attendee matters to that sponsor.

Also identifies sponsor team members already in the attendee pool.

Usage:
    cd backend && source .venv/bin/activate

    # Generate reports for all sponsors (from Google Sheet data):
    python scripts/sponsor_intelligence.py

    # Generate report for a single sponsor:
    python scripts/sponsor_intelligence.py --sponsor "Zircuit"

    # Dry-run (shows matches, no PDF/HTML output):
    python scripts/sponsor_intelligence.py --dry-run

    # Output HTML reports to a directory:
    python scripts/sponsor_intelligence.py --output-dir /tmp/sponsor_reports

    # Also identify sponsor team members in the attendee pool:
    python scripts/sponsor_intelligence.py --identify-team
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from openai import AsyncOpenAI

# ── Sponsor data (from Google Sheet: POT 2026 Sponsorship Tracker) ────────
SPONSORS = [
    {"name": "Zircuit",              "value": 50000,  "tier": "Gold",     "lead": "Karl"},
    {"name": "CertiK",              "value": 49000,  "tier": "Platinum", "lead": "Karl"},
    {"name": "BPI France",          "value": 20000,  "tier": "Silver",   "lead": "Karl"},
    {"name": "Taostats",            "value": 116000, "tier": "Diamond",  "lead": "Paul"},
    {"name": "V3V Ventures",        "value": 40000,  "tier": "Gold",     "lead": "William"},
    {"name": "Naoris Protocol",     "value": 55000,  "tier": "Gold",     "lead": "William"},
    {"name": "Cryptomarkt",         "value": 15000,  "tier": "Silver",   "lead": "William"},
    {"name": "XBTO",               "value": 35000,  "tier": "Gold",     "lead": "Kate"},
    {"name": "Spectrum",            "value": 60000,  "tier": "Platinum", "lead": "Kate"},
    {"name": "Rain",               "value": 40000,  "tier": "Gold",     "lead": "Nupur"},
    {"name": "Edge & Node",        "value": 65000,  "tier": "Platinum", "lead": "Nupur"},
    {"name": "BitGo",              "value": 55000,  "tier": "Gold",     "lead": "Karl"},
    {"name": "BitMEX",             "value": 25000,  "tier": "Gold",     "lead": "Karl"},
    {"name": "Paxos",              "value": 25000,  "tier": "Silver",   "lead": "William"},
    {"name": "Morph Network",      "value": 35000,  "tier": "Gold",     "lead": "Nupur"},
    {"name": "DFG",                "value": 45000,  "tier": "Gold",     "lead": "William"},
    {"name": "Enlivex",            "value": 30000,  "tier": "Gold",     "lead": "William"},
    {"name": "SimplyTAO",          "value": 30000,  "tier": "Gold",     "lead": "William"},
    {"name": "Nexus Mutual",       "value": 30000,  "tier": "Gold",     "lead": "William"},
    {"name": "ChangeNow",          "value": 70000,  "tier": "Platinum", "lead": "William"},
    {"name": "21X",                "value": 70000,  "tier": "Platinum", "lead": "William"},
    {"name": "Teroxx",             "value": 35000,  "tier": "Gold",     "lead": "William"},
    {"name": "Holonym",            "value": 8000,   "tier": "Startup",  "lead": "William"},
    {"name": "MatterFi",           "value": 12000,  "tier": "Silver",   "lead": "William"},
]

# ── Grid integration (reuse the hardened service) ─────────────────────────
from app.services.grid_enrichment import enrich_from_grid


def build_sponsor_composite_text(sponsor: dict, grid: dict | None) -> str:
    """Build embedding text for a sponsor company."""
    parts = [f"Company: {sponsor['name']}"]
    parts.append(f"Sponsorship Tier: {sponsor['tier']}")

    if grid:
        if grid.get("grid_description"):
            parts.append(f"Description (Grid verified): {grid['grid_description']}")
        if grid.get("grid_description_long"):
            parts.append(f"Full Description: {grid['grid_description_long'][:300]}")
        if grid.get("grid_sector"):
            parts.append(f"Sector: {grid['grid_sector']}")
        if grid.get("grid_type"):
            parts.append(f"Company Type: {grid['grid_type']}")
        products = grid.get("grid_products") or []
        if products:
            product_lines = []
            for p in products[:5]:
                desc = f": {p.get('description', '')}" if p.get("description") else ""
                product_lines.append(f"{p['name']}{desc}")
            parts.append(f"Products: {'; '.join(product_lines)}")
    else:
        parts.append(f"Sponsor at Proof of Talk 2026 Web3 conference")

    return "\n".join(parts)


async def generate_embedding(openai_client: AsyncOpenAI, text: str) -> list[float]:
    """Generate embedding for sponsor composite text."""
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


async def find_relevant_attendees(
    db_url: str, embedding: list[float], top_k: int = 20
) -> list[dict]:
    """Query pgvector for attendees most relevant to the sponsor embedding."""
    import asyncpg

    # Convert asyncpg URL format
    conn_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_url)

    emb_str = "[" + ",".join(str(v) for v in embedding) + "]"

    rows = await conn.fetch("""
        SELECT
            id, name, email, title, company, company_website,
            goals, ticket_type, ai_summary, vertical_tags, intent_tags,
            deal_readiness_score, enriched_profile,
            1 - (embedding <=> $1::vector) as similarity
        FROM attendees
        WHERE embedding IS NOT NULL
          AND id NOT IN (
              SELECT attendee_id FROM users
              WHERE is_admin = true AND attendee_id IS NOT NULL
          )
        ORDER BY embedding <=> $1::vector
        LIMIT $2
    """, emb_str, top_k)

    await conn.close()

    attendees = []
    for r in rows:
        enriched = json.loads(r["enriched_profile"]) if r["enriched_profile"] else {}
        grid = enriched.get("grid") or {}
        attendees.append({
            "id": str(r["id"]),
            "name": r["name"],
            "email": r["email"],
            "title": r["title"] or "",
            "company": r["company"] or "",
            "company_website": r["company_website"] or "",
            "goals": r["goals"] or "",
            "ticket_type": r["ticket_type"] or "",
            "ai_summary": r["ai_summary"] or "",
            "vertical_tags": r["vertical_tags"] or [],
            "intent_tags": r["intent_tags"] or [],
            "deal_readiness": r["deal_readiness_score"] or 0,
            "similarity": float(r["similarity"]),
            "grid_name": grid.get("grid_name", ""),
            "grid_sector": grid.get("grid_sector", ""),
        })

    return attendees


async def identify_sponsor_team(
    db_url: str, sponsor_name: str
) -> list[dict]:
    """Find attendees who work for the sponsor company."""
    import asyncpg

    conn_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(conn_url)

    # Search by company name (fuzzy) and email domain
    name_pattern = f"%{sponsor_name.lower()}%"
    rows = await conn.fetch("""
        SELECT id, name, email, title, company, ticket_type
        FROM attendees
        WHERE LOWER(company) LIKE $1
           OR LOWER(email) LIKE $1
    """, name_pattern)

    await conn.close()

    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "email": r["email"],
            "title": r["title"] or "",
            "company": r["company"] or "",
            "ticket_type": r["ticket_type"] or "",
        }
        for r in rows
    ]


async def generate_sponsor_explanations(
    openai_client: AsyncOpenAI,
    sponsor: dict,
    grid: dict | None,
    attendees: list[dict],
) -> list[dict]:
    """Use GPT-4o to explain why each attendee matters to this sponsor."""
    grid_context = ""
    if grid:
        products = ", ".join(p["name"] for p in (grid.get("grid_products") or [])[:5])
        grid_context = f"""
Grid Verified Company Data:
- Description: {grid.get('grid_description', 'N/A')}
- Sector: {grid.get('grid_sector', 'N/A')}
- Type: {grid.get('grid_type', 'N/A')}
- Products: {products or 'N/A'}
"""

    attendee_blocks = []
    for i, a in enumerate(attendees[:20]):
        attendee_blocks.append(
            f"Attendee {i+1}:\n"
            f"  Name: {a['name']}\n"
            f"  Title: {a['title']}\n"
            f"  Company: {a['company']}\n"
            f"  Ticket: {a['ticket_type']}\n"
            f"  Goals: {a['goals'][:200] if a['goals'] else 'Not specified'}\n"
            f"  AI Summary: {a['ai_summary'][:200] if a['ai_summary'] else 'N/A'}\n"
            f"  Sectors: {', '.join(a['vertical_tags'][:3])}\n"
            f"  Intent: {', '.join(a['intent_tags'][:3])}\n"
            f"  Deal Readiness: {a['deal_readiness']:.0%}\n"
            f"  Relevance Score: {a['similarity']:.3f}"
        )

    prompt = f"""You are generating a sponsor intelligence report for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace with 2,500 decision-makers.

SPONSOR COMPANY: {sponsor['name']}
Sponsorship Tier: {sponsor['tier']} (€{sponsor['value']:,})
{grid_context}

CANDIDATE ATTENDEES (ranked by AI relevance):
{chr(10).join(attendee_blocks)}

For each attendee, generate a JSON entry explaining why they matter to {sponsor['name']} specifically.
Focus on:
- What concrete value this meeting could create for the sponsor (deal, partnership, integration, customer)
- Specific conversation openers based on the attendee's goals and the sponsor's products
- Deal readiness level: HIGH (ready to transact), MEDIUM (exploratory), LOW (awareness/networking)

Return a JSON array:
[
  {{
    "attendee_index": 1,
    "relevance": "HIGH" | "MEDIUM" | "LOW",
    "why_they_matter": "2-3 sentences — be specific about mutual value, reference products, mandates, sectors",
    "conversation_opener": "One specific opening line or topic",
    "deal_potential": "What could realistically come from this meeting"
  }}
]

Return ONLY the JSON array. No markdown, no commentary. Rank from most to least valuable for {sponsor['name']}."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"  ⚠️  Failed to parse GPT response for {sponsor['name']}")
        return []


def generate_html_report(
    sponsor: dict,
    grid: dict | None,
    attendees: list[dict],
    explanations: list[dict],
    team_members: list[dict],
) -> str:
    """Generate a branded HTML intelligence report."""
    grid_section = ""
    if grid:
        sector = grid.get("grid_sector", "")
        products = ", ".join(p["name"] for p in (grid.get("grid_products") or [])[:5])
        grid_section = f"""
        <div class="grid-badge">
            <span class="verified">✓ Verified by The Grid</span>
            <span class="sector">{sector}</span>
        </div>
        <p class="description">{grid.get('grid_description', '')}</p>
        {f'<p class="products"><strong>Products:</strong> {products}</p>' if products else ''}
        """

    # Build attendee rows
    attendee_rows = ""
    for exp in explanations[:20]:
        idx = exp.get("attendee_index", 1) - 1
        if idx < 0 or idx >= len(attendees):
            continue
        a = attendees[idx]

        relevance_color = {
            "HIGH": "#34d399",
            "MEDIUM": "#fbbf24",
            "LOW": "#94a3b8",
        }.get(exp.get("relevance", "LOW"), "#94a3b8")

        grid_tag = ""
        if a.get("grid_name"):
            grid_tag = f'<span class="tag grid-tag">Grid: {a["grid_sector"]}</span>'

        attendee_rows += f"""
        <div class="attendee-card">
            <div class="attendee-header">
                <div>
                    <span class="rank">#{idx + 1}</span>
                    <strong>{a['name']}</strong>
                    <span class="role">{a['title']}{' · ' + a['company'] if a['company'] else ''}</span>
                </div>
                <div>
                    <span class="relevance" style="background: {relevance_color}">{exp.get('relevance', 'LOW')}</span>
                    <span class="ticket">{a['ticket_type']}</span>
                </div>
            </div>
            <div class="attendee-body">
                <p class="why">{exp.get('why_they_matter', '')}</p>
                <div class="opener"><strong>Open with:</strong> {exp.get('conversation_opener', '')}</div>
                <div class="deal"><strong>Deal potential:</strong> {exp.get('deal_potential', '')}</div>
                <div class="tags">
                    {' '.join(f'<span class="tag">{t.replace("_", " ").title()}</span>' for t in a.get('vertical_tags', [])[:3])}
                    {grid_tag}
                </div>
            </div>
        </div>
        """

    # Team members section
    team_section = ""
    if team_members:
        team_rows = ""
        for tm in team_members:
            team_rows += f"<li><strong>{tm['name']}</strong> — {tm['title']} ({tm['ticket_type']})</li>"
        team_section = f"""
        <div class="section">
            <h2>Your Team at POT 2026</h2>
            <p>These people from {sponsor['name']} are already registered:</p>
            <ul>{team_rows}</ul>
        </div>
        """

    # Summary stats
    high_count = sum(1 for e in explanations if e.get("relevance") == "HIGH")
    medium_count = sum(1 for e in explanations if e.get("relevance") == "MEDIUM")
    low_count = sum(1 for e in explanations if e.get("relevance") == "LOW")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{sponsor['name']} — POT 2026 Intelligence Briefing</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{ --orange: #E76315; --dark: #0d0d1a; --card: #13131f; --border: rgba(255,255,255,0.06); --text: #e8e8f0; --muted: rgba(255,255,255,0.4); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: var(--dark); color: var(--text); font-family: 'DM Sans', sans-serif; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
.page {{ max-width: 900px; margin: 0 auto; padding: 60px 32px 80px; }}
.hero {{ text-align: center; padding: 60px 0 40px; }}
.hero h1 {{ font-family: 'Instrument Serif', serif; font-size: 42px; font-weight: 400; margin-bottom: 8px; }}
.hero h1 em {{ color: var(--orange); font-style: italic; }}
.hero .subtitle {{ color: var(--muted); font-size: 15px; }}
.badge {{ display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--orange); border: 1px solid rgba(231,99,21,0.3); padding: 6px 16px; border-radius: 100px; margin-bottom: 24px; }}
.stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--border); border-radius: 12px; overflow: hidden; margin: 32px 0; }}
.stat {{ background: var(--card); padding: 20px; text-align: center; }}
.stat .num {{ font-family: 'Instrument Serif', serif; font-size: 28px; color: var(--orange); }}
.stat .label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 4px; }}
.grid-badge {{ margin: 16px 0; }}
.verified {{ background: rgba(16,185,129,0.1); color: #34d399; padding: 4px 12px; border-radius: 100px; font-size: 12px; font-weight: 600; }}
.sector {{ background: rgba(167,139,250,0.1); color: #a78bfa; padding: 4px 12px; border-radius: 100px; font-size: 12px; margin-left: 8px; }}
.description {{ color: var(--muted); font-size: 14px; margin: 8px 0; }}
.products {{ font-size: 13px; color: rgba(255,255,255,0.6); }}
.section {{ margin: 48px 0; }}
.section h2 {{ font-family: 'Instrument Serif', serif; font-size: 28px; font-weight: 400; margin-bottom: 16px; }}
.attendee-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 16px; }}
.attendee-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
.rank {{ color: var(--orange); font-family: 'Instrument Serif', serif; font-size: 20px; margin-right: 8px; }}
.role {{ color: var(--muted); font-size: 13px; display: block; margin-top: 2px; }}
.relevance {{ padding: 3px 10px; border-radius: 100px; font-size: 11px; font-weight: 600; color: #0d0d1a; }}
.ticket {{ color: var(--muted); font-size: 11px; margin-left: 8px; text-transform: uppercase; }}
.why {{ font-size: 14px; margin-bottom: 10px; color: rgba(255,255,255,0.8); }}
.opener, .deal {{ font-size: 13px; color: rgba(255,255,255,0.6); margin-bottom: 4px; }}
.tags {{ margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }}
.tag {{ font-size: 11px; padding: 3px 10px; border-radius: 100px; background: rgba(231,99,21,0.1); color: var(--orange); }}
.grid-tag {{ background: rgba(16,185,129,0.1); color: #34d399; }}
.footer {{ text-align: center; margin-top: 48px; font-size: 12px; color: rgba(255,255,255,0.2); }}
ul {{ padding-left: 20px; }} li {{ margin: 6px 0; font-size: 14px; }}
@media (max-width: 640px) {{ .stats {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<div class="page">
    <div class="hero">
        <div class="badge">{sponsor['tier']} Sponsor · Confidential</div>
        <h1>{sponsor['name']} — <em>Intelligence Briefing</em></h1>
        <p class="subtitle">Proof of Talk 2026 · Louvre Palace, Paris · June 2–3</p>
        {grid_section}
    </div>

    <div class="stats">
        <div class="stat"><div class="num">{len(explanations)}</div><div class="label">Target attendees</div></div>
        <div class="stat"><div class="num">{high_count}</div><div class="label">High relevance</div></div>
        <div class="stat"><div class="num">{medium_count}</div><div class="label">Medium</div></div>
        <div class="stat"><div class="num">{len(team_members)}</div><div class="label">Your team attending</div></div>
    </div>

    {team_section}

    <div class="section">
        <h2>Your Top {len(explanations)} Targets</h2>
        {attendee_rows}
    </div>

    <div class="footer">
        Proof of Talk 2026 · Sponsor Intelligence Report · Generated {datetime.now().strftime('%B %d, %Y')} · Confidential
    </div>
</div>
</body>
</html>"""


async def generate_report_for_sponsor(
    sponsor: dict,
    openai_client: AsyncOpenAI,
    db_url: str,
    output_dir: str | None = None,
    dry_run: bool = False,
    identify_team: bool = False,
) -> dict:
    """Full pipeline for one sponsor."""
    print(f"\n{'='*60}")
    print(f"  {sponsor['name']} ({sponsor['tier']}, €{sponsor['value']:,})")
    print(f"{'='*60}")

    # 1. Query The Grid (reuses hardened service with retries + case variants)
    grid = await enrich_from_grid(sponsor["name"])
    if grid:
        sector = grid.get("grid_sector", "—")
        products = [p["name"] for p in (grid.get("grid_products") or [])[:3]]
        print(f"  ✅ Grid: {grid['grid_name']} | {sector} | products: {', '.join(products) or 'none'}")
    else:
        print(f"  ❌ Grid: not found — using sponsor name only")

    # 2. Build composite text + embed
    composite = build_sponsor_composite_text(sponsor, grid)
    print(f"  📝 Composite text: {len(composite)} chars")

    embedding = await generate_embedding(openai_client, composite)
    print(f"  🔢 Embedding: {len(embedding)} dimensions")

    # 3. Find relevant attendees via pgvector
    attendees = await find_relevant_attendees(db_url, embedding, top_k=25)
    print(f"  🎯 Found {len(attendees)} relevant attendees (top similarity: {attendees[0]['similarity']:.3f})")

    # 4. Identify team members
    team_members = []
    if identify_team:
        team_members = await identify_sponsor_team(db_url, sponsor["name"])
        if team_members:
            print(f"  👥 Team members attending: {len(team_members)}")
            for tm in team_members:
                print(f"     - {tm['name']} ({tm['title']}, {tm['ticket_type']})")
        else:
            print(f"  👥 No team members found in attendee pool")

    if dry_run:
        print(f"\n  Top 5 matches:")
        for i, a in enumerate(attendees[:5]):
            print(f"    {i+1}. {a['name']:25s} {a['title']:25s} {a['company']:20s} sim={a['similarity']:.3f}")
        return {"sponsor": sponsor["name"], "attendees": len(attendees), "team": len(team_members)}

    # 5. GPT-4o explanations
    print(f"  🤖 Generating explanations...")
    explanations = await generate_sponsor_explanations(openai_client, sponsor, grid, attendees)
    print(f"  ✅ Generated {len(explanations)} explanations")

    high = sum(1 for e in explanations if e.get("relevance") == "HIGH")
    medium = sum(1 for e in explanations if e.get("relevance") == "MEDIUM")
    print(f"     HIGH: {high} | MEDIUM: {medium} | LOW: {len(explanations) - high - medium}")

    # 6. Generate HTML report
    if output_dir:
        html = generate_html_report(sponsor, grid, attendees, explanations, team_members)
        slug = sponsor["name"].lower().replace(" ", "-").replace("&", "and")
        filepath = os.path.join(output_dir, f"{slug}-intelligence.html")
        with open(filepath, "w") as f:
            f.write(html)
        print(f"  📄 Report saved: {filepath}")

    return {
        "sponsor": sponsor["name"],
        "grid_found": grid is not None,
        "attendees_matched": len(attendees),
        "explanations": len(explanations),
        "high_relevance": high,
        "team_members": len(team_members),
    }


async def main():
    parser = argparse.ArgumentParser(description="Generate sponsor intelligence reports")
    parser.add_argument("--sponsor", help="Generate for a single sponsor (by name)")
    parser.add_argument("--dry-run", action="store_true", help="Show matches without generating reports")
    parser.add_argument("--output-dir", default=None, help="Directory for HTML reports")
    parser.add_argument("--identify-team", action="store_true", help="Find sponsor team members in attendee pool")
    parser.add_argument("--top-k", type=int, default=20, help="Number of target attendees per sponsor")
    args = parser.parse_args()

    # Load env
    from dotenv import load_dotenv
    load_dotenv()

    openai_key = os.getenv("OPENAI_API_KEY")
    db_url = os.getenv("DATABASE_URL")

    if not openai_key:
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)
    if not db_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)

    openai_client = AsyncOpenAI(api_key=openai_key)

    # Output directory
    output_dir = args.output_dir
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    elif not args.dry_run:
        output_dir = str(Path(__file__).resolve().parent.parent / "data" / "sponsor_reports")
        os.makedirs(output_dir, exist_ok=True)

    # Filter sponsors
    sponsors = SPONSORS
    if args.sponsor:
        sponsors = [s for s in SPONSORS if s["name"].lower() == args.sponsor.lower()]
        if not sponsors:
            # Fuzzy match
            sponsors = [s for s in SPONSORS if args.sponsor.lower() in s["name"].lower()]
        if not sponsors:
            print(f"❌ Sponsor '{args.sponsor}' not found. Available: {', '.join(s['name'] for s in SPONSORS)}")
            sys.exit(1)

    print(f"\n🚀 Generating intelligence reports for {len(sponsors)} sponsor(s)")
    print(f"   Database: {db_url[:50]}...")
    print(f"   Output: {output_dir or '(dry-run)'}")

    results = []
    for sponsor in sponsors:
        result = await generate_report_for_sponsor(
            sponsor,
            openai_client,
            db_url,
            output_dir=output_dir,
            dry_run=args.dry_run,
            identify_team=args.identify_team,
        )
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Sponsor':25s} {'Grid':5s} {'Targets':8s} {'High':5s} {'Team':5s}")
    print(f"  {'-'*48}")
    for r in results:
        grid_icon = "✅" if r.get("grid_found") else "❌"
        print(f"  {r['sponsor']:25s} {grid_icon:5s} {r.get('attendees_matched', r.get('attendees', 0)):8d} {r.get('high_relevance', '—'):>5} {r.get('team_members', 0):5d}")

    if output_dir and not args.dry_run:
        print(f"\n  📁 Reports saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
