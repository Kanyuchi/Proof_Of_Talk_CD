#!/usr/bin/env python3
"""
Proof of Talk 2026 — AI Matchmaking Engine Demo
================================================
Runs the 5 test profiles through the full matching pipeline:
  1. Load profiles from seed data
  2. Generate AI summaries for each attendee
  3. Classify intents (deploying_capital, raising_capital, etc.)
  4. Generate embeddings (OpenAI text-embedding-3-small)
  5. Compute pairwise similarity scores
  6. Use GPT-4o to rank matches and generate explanations
  7. Output prioritised match recommendations per attendee

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/demo_matching.py

Requires OPENAI_API_KEY in backend/.env
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from openai import AsyncOpenAI
import numpy as np

# ── Config ──────────────────────────────────────────────────────────────

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"

api_key = os.getenv("OPENAI_API_KEY", "")
client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global client
    if client is None:
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in .env")
            print("Create backend/.env with: OPENAI_API_KEY=sk-...")
            sys.exit(1)
        client = AsyncOpenAI(api_key=api_key)
    return client


# ── Data Structures ─────────────────────────────────────────────────────

@dataclass
class AttendeeProfile:
    name: str
    email: str
    company: str
    title: str
    ticket_type: str
    interests: list[str]
    goals: str
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    company_website: str | None = None
    ai_summary: str = ""
    intent_tags: list[str] = field(default_factory=list)
    deal_readiness: float = 0.0
    embedding: list[float] = field(default_factory=list)


@dataclass
class MatchResult:
    attendee_a: str
    attendee_b: str
    similarity_score: float
    complementary_score: float
    overall_score: float
    match_type: str
    explanation: str
    shared_context: dict


# ── Pipeline Functions ──────────────────────────────────────────────────

def build_composite_text(p: AttendeeProfile) -> str:
    """Build rich text blob from all attendee data for embedding."""
    parts = [
        f"Name: {p.name}",
        f"Title: {p.title}",
        f"Company: {p.company}",
        f"Ticket Type: {p.ticket_type}",
        f"Interests: {', '.join(p.interests)}",
        f"Goals: {p.goals}",
    ]
    if p.ai_summary:
        parts.append(f"Profile Summary: {p.ai_summary}")
    return "\n".join(parts)


async def generate_ai_summary(p: AttendeeProfile) -> str:
    """Generate a concise AI summary of the attendee."""
    prompt = f"""You are an AI assistant for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace (2,500 decision-makers, $18T AUM).

Generate a concise 2-3 sentence professional summary capturing:
- Their role and what their organization does
- What they're actively looking for at this event
- Their deal-readiness and decision-making authority

Name: {p.name}
Title: {p.title}
Company: {p.company}
Ticket Type: {p.ticket_type}
Interests: {', '.join(p.interests)}
Goals: {p.goals}

Write in third person. Be specific. No generic language."""

    resp = await _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


async def classify_intents(p: AttendeeProfile) -> list[str]:
    """Classify attendee intents into structured tags."""
    prompt = f"""Classify this conference attendee's intents into structured tags.

Attendee: {p.name}, {p.title} at {p.company}
Goals: {p.goals}
Interests: {', '.join(p.interests)}

Return ONLY a JSON array from this taxonomy:
- "deploying_capital" (actively investing/allocating)
- "raising_capital" (seeking funding)
- "seeking_partnerships" (business development)
- "seeking_customers" (sales pipeline)
- "regulatory_engagement" (policy/compliance discussions)
- "technology_evaluation" (assessing tech solutions)
- "deal_making" (ready to transact)
- "knowledge_exchange" (learning/sharing expertise)
- "co_investment" (seeking co-investors)

Return 2-4 most relevant tags as a JSON array. Nothing else."""

    resp = await _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100,
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"    [WARN] Intent parse failed for raw: {raw[:100]}")
        return ["knowledge_exchange"]


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding via OpenAI."""
    resp = await _get_client().embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


async def rank_matches_for_attendee(
    target: AttendeeProfile,
    candidates: list[tuple[AttendeeProfile, float]],
) -> list[dict]:
    """Use GPT-4o to re-rank and explain matches."""
    candidate_descriptions = []
    for i, (c, sim) in enumerate(candidates):
        candidate_descriptions.append(
            f"Candidate {i+1}:\n"
            f"  Name: {c.name}\n"
            f"  Title: {c.title}\n"
            f"  Company: {c.company}\n"
            f"  Goals: {c.goals}\n"
            f"  Interests: {', '.join(c.interests)}\n"
            f"  AI Summary: {c.ai_summary}\n"
            f"  Intent Tags: {', '.join(c.intent_tags)}\n"
            f"  Deal Readiness: {c.deal_readiness:.2f}\n"
            f"  Vector Similarity: {sim:.3f}"
        )

    prompt = f"""You are the AI matchmaking engine for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace with 2,500 decision-makers controlling $18 trillion in assets.

Re-rank and explain match recommendations. Go beyond surface-level keyword matching. Find:
1. **Complementary matches** — one party has what the other needs (investor meets startup, regulator meets builder)
2. **Non-obvious connections** — different sectors solving similar underlying problems
3. **Deal-ready pairs** — both parties positioned to transact, not just network

TARGET ATTENDEE:
Name: {target.name}
Title: {target.title}
Company: {target.company}
Goals: {target.goals}
Interests: {', '.join(target.interests)}
AI Summary: {target.ai_summary}
Intent Tags: {', '.join(target.intent_tags)}
Deal Readiness: {target.deal_readiness:.2f}

CANDIDATES:
{chr(10).join(candidate_descriptions)}

Return a JSON array ranked best to worst. Each entry:
{{
  "candidate_index": <1-based>,
  "overall_score": <0.0-1.0>,
  "complementary_score": <0.0-1.0>,
  "match_type": "complementary" | "non_obvious" | "deal_ready",
  "explanation": "<2-3 sentences: WHY these two should meet. Be specific — reference funding amounts, products, mandates, mutual needs.>",
  "shared_context": {{
    "sectors": ["overlapping sectors"],
    "synergies": ["specific synergy points"],
    "action_items": ["suggested conversation topics or deals"]
  }}
}}

Return ONLY the JSON array."""

    resp = await _get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=3000,
    )

    raw = resp.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"    [WARN] Rank parse failed, using similarity fallback. Raw: {raw[:200]}")
        return [
            {
                "candidate_index": i + 1,
                "overall_score": sim,
                "complementary_score": sim,
                "match_type": "complementary",
                "explanation": "Match based on profile similarity.",
                "shared_context": {},
            }
            for i, (_, sim) in enumerate(candidates)
        ]


# ── Main Pipeline ───────────────────────────────────────────────────────

async def run_demo():
    print("=" * 80)
    print("PROOF OF TALK 2026 — AI MATCHMAKING ENGINE DEMO")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Models: {EMBEDDING_MODEL} (embeddings) + {CHAT_MODEL} (reasoning)")
    print()

    # ── Load Profiles ───────────────────────────────────────────────────
    seed_file = Path(__file__).parent.parent / "data" / "seed_profiles.json"
    with open(seed_file) as f:
        raw_profiles = json.load(f)

    profiles = [AttendeeProfile(**p) for p in raw_profiles]
    print(f"Loaded {len(profiles)} test profiles:")
    for p in profiles:
        print(f"  - {p.name} | {p.title} | {p.company}")
    print()

    # ── Stage 1: AI Summaries ───────────────────────────────────────────
    print("STAGE 1: Generating AI Summaries...")
    print("-" * 40)
    for p in profiles:
        p.ai_summary = await generate_ai_summary(p)
        print(f"\n  [{p.name}]")
        print(f"  {p.ai_summary}")
    print()

    # ── Stage 2: Intent Classification ──────────────────────────────────
    print("STAGE 2: Classifying Intents...")
    print("-" * 40)
    deal_signals = {"deploying_capital", "raising_capital", "deal_making", "seeking_customers"}
    for p in profiles:
        p.intent_tags = await classify_intents(p)
        p.deal_readiness = len(set(p.intent_tags) & deal_signals) / len(deal_signals)
        print(f"  [{p.name}] {p.intent_tags} (deal readiness: {p.deal_readiness:.2f})")
    print()

    # ── Stage 3: Embeddings ─────────────────────────────────────────────
    print("STAGE 3: Generating Embeddings...")
    print("-" * 40)
    for p in profiles:
        text = build_composite_text(p)
        p.embedding = await generate_embedding(text)
        print(f"  [{p.name}] Embedded ({len(p.embedding)} dimensions)")
    print()

    # ── Stage 4: Pairwise Similarity Matrix ─────────────────────────────
    print("STAGE 4: Computing Similarity Matrix...")
    print("-" * 40)
    n = len(profiles)
    sim_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                sim_matrix[i][j] = cosine_similarity(profiles[i].embedding, profiles[j].embedding)

    # Print similarity matrix
    names_short = [p.name.split()[0] for p in profiles]  # First names
    header = "           " + "  ".join(f"{n:>10}" for n in names_short)
    print(header)
    for i, p in enumerate(profiles):
        row = f"{names_short[i]:>10} " + "  ".join(
            f"{sim_matrix[i][j]:>10.3f}" if i != j else f"{'---':>10}"
            for j in range(n)
        )
        print(row)
    print()

    # ── Stage 5: AI-Powered Match Ranking ───────────────────────────────
    print("STAGE 5: AI Match Ranking & Explanations")
    print("=" * 80)

    all_results = {}

    for i, target in enumerate(profiles):
        # Get candidates sorted by similarity
        candidates = [
            (profiles[j], sim_matrix[i][j])
            for j in range(n) if i != j
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)

        print(f"\n{'=' * 80}")
        print(f"MATCHES FOR: {target.name}")
        print(f"  {target.title} | {target.company}")
        print(f"  Goals: {target.goals[:100]}...")
        print(f"  Intents: {', '.join(target.intent_tags)}")
        print(f"  Deal Readiness: {target.deal_readiness:.2f}")
        print(f"{'=' * 80}")

        ranked = await rank_matches_for_attendee(target, candidates)
        all_results[target.name] = ranked

        for rank, entry in enumerate(ranked, 1):
            idx = entry["candidate_index"] - 1
            if idx < 0 or idx >= len(candidates):
                continue
            candidate, sim_score = candidates[idx]

            match_type_icon = {
                "complementary": "🤝",
                "non_obvious": "💡",
                "deal_ready": "💰",
            }.get(entry.get("match_type", ""), "📌")

            print(f"\n  #{rank} {match_type_icon} {candidate.name}")
            print(f"     {candidate.title} | {candidate.company}")
            print(f"     Type: {entry.get('match_type', 'N/A')} | Score: {entry.get('overall_score', 0):.2f} | Similarity: {sim_score:.3f}")
            print(f"     WHY: {entry.get('explanation', 'N/A')}")

            ctx = entry.get("shared_context", {})
            if ctx.get("synergies"):
                print(f"     Synergies: {', '.join(ctx['synergies'])}")
            if ctx.get("action_items"):
                print(f"     Action Items: {', '.join(ctx['action_items'])}")

    # ── Save Results ────────────────────────────────────────────────────
    output_dir = Path(__file__).parent.parent / "data"
    output_file = output_dir / "demo_results.json"

    output = {
        "generated_at": datetime.now().isoformat(),
        "models": {"embedding": EMBEDDING_MODEL, "chat": CHAT_MODEL},
        "profiles": [
            {
                "name": p.name,
                "title": p.title,
                "company": p.company,
                "ai_summary": p.ai_summary,
                "intent_tags": p.intent_tags,
                "deal_readiness": p.deal_readiness,
            }
            for p in profiles
        ],
        "similarity_matrix": {
            profiles[i].name: {
                profiles[j].name: round(sim_matrix[i][j], 4)
                for j in range(n) if i != j
            }
            for i in range(n)
        },
        "match_recommendations": all_results,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"DEMO COMPLETE")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(run_demo())
