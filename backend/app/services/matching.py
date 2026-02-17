import json
import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.models.attendee import Attendee, Match
from app.services.embeddings import embed_attendee, generate_ai_summary, classify_intents

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class MatchingEngine:
    """3-stage AI matchmaking pipeline: Embed -> Retrieve -> Rank & Explain."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Stage 1: Embed ──────────────────────────────────────────────────

    async def process_attendee(self, attendee: Attendee) -> Attendee:
        """Generate AI summary, intent tags, and embedding for an attendee."""
        # Generate AI summary
        attendee.ai_summary = await generate_ai_summary(attendee)

        # Classify intents
        attendee.intent_tags = await classify_intents(attendee)

        # Compute deal-readiness score based on intents
        deal_signals = {"deploying_capital", "raising_capital", "deal_making", "seeking_customers"}
        matching_intents = set(attendee.intent_tags) & deal_signals
        attendee.deal_readiness_score = len(matching_intents) / len(deal_signals)

        # Generate embedding
        attendee.embedding = await embed_attendee(attendee)

        self.db.add(attendee)
        await self.db.commit()
        await self.db.refresh(attendee)
        return attendee

    async def process_all_attendees(self) -> int:
        """Process all attendees that don't have embeddings yet."""
        result = await self.db.execute(
            select(Attendee).where(Attendee.embedding.is_(None))
        )
        attendees = result.scalars().all()
        for attendee in attendees:
            await self.process_attendee(attendee)
        return len(attendees)

    # ── Stage 2: Retrieve (pgvector similarity) ─────────────────────────

    async def retrieve_candidates(
        self, attendee: Attendee, top_k: int = 10
    ) -> list[tuple[Attendee, float]]:
        """Find top-K most similar attendees using pgvector cosine distance."""
        if attendee.embedding is None:
            attendee = await self.process_attendee(attendee)

        # pgvector cosine distance: <=> operator (lower = more similar)
        query = text("""
            SELECT id, 1 - (embedding <=> :embedding) as similarity
            FROM attendees
            WHERE id != :attendee_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :top_k
        """)

        result = await self.db.execute(
            query,
            {
                "embedding": str(attendee.embedding),
                "attendee_id": str(attendee.id),
                "top_k": top_k,
            },
        )
        rows = result.fetchall()

        candidates = []
        for row in rows:
            candidate = await self.db.get(Attendee, row.id)
            if candidate:
                candidates.append((candidate, float(row.similarity)))

        return candidates

    # ── Stage 3: Rank & Explain (GPT-4o) ────────────────────────────────

    async def rank_and_explain(
        self,
        attendee: Attendee,
        candidates: list[tuple[Attendee, float]],
    ) -> list[dict]:
        """Use GPT-4o to re-rank candidates and generate match explanations."""
        if not candidates:
            return []

        candidate_descriptions = []
        for i, (candidate, sim_score) in enumerate(candidates):
            candidate_descriptions.append(
                f"Candidate {i+1}:\n"
                f"  Name: {candidate.name}\n"
                f"  Title: {candidate.title}\n"
                f"  Company: {candidate.company}\n"
                f"  Goals: {candidate.goals or 'Not specified'}\n"
                f"  Interests: {', '.join(candidate.interests) if candidate.interests else 'Not specified'}\n"
                f"  AI Summary: {candidate.ai_summary or 'Not available'}\n"
                f"  Intent Tags: {', '.join(candidate.intent_tags) if candidate.intent_tags else 'Not classified'}\n"
                f"  Deal Readiness: {candidate.deal_readiness_score or 0:.2f}\n"
                f"  Vector Similarity: {sim_score:.3f}"
            )

        prompt = f"""You are the AI matchmaking engine for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace with 2,500 decision-makers controlling $18 trillion in assets.

Your task: Re-rank and explain match recommendations for the attendee below. Go beyond surface-level keyword matching. Find:
1. **Complementary matches** — where one party has what the other needs (investor meets startup, regulator meets builder)
2. **Non-obvious connections** — different sectors but solving similar underlying problems
3. **Deal-ready pairs** — both parties in a position to transact, not just talk

TARGET ATTENDEE:
Name: {attendee.name}
Title: {attendee.title}
Company: {attendee.company}
Goals: {attendee.goals or 'Not specified'}
Interests: {', '.join(attendee.interests) if attendee.interests else 'Not specified'}
AI Summary: {attendee.ai_summary or 'Not available'}
Intent Tags: {', '.join(attendee.intent_tags) if attendee.intent_tags else 'Not classified'}
Deal Readiness: {attendee.deal_readiness_score or 0:.2f}

CANDIDATES:
{chr(10).join(candidate_descriptions)}

Return a JSON array ranked from best to worst match. Each entry:
{{
  "candidate_index": <1-based index>,
  "overall_score": <0.0-1.0>,
  "complementary_score": <0.0-1.0>,
  "match_type": "complementary" | "non_obvious" | "deal_ready",
  "explanation": "<2-3 sentences explaining WHY these two should meet. Be specific about the mutual value. Reference concrete details like funding amounts, products, mandates.>",
  "shared_context": {{
    "sectors": ["list of shared/overlapping sectors"],
    "synergies": ["specific synergy points"],
    "action_items": ["suggested conversation topics or deals to discuss"]
  }}
}}

Return ONLY the JSON array. No markdown, no commentary."""

        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000,
        )

        try:
            ranked = json.loads(response.choices[0].message.content.strip())
        except json.JSONDecodeError:
            # Fallback: return candidates in similarity order
            ranked = [
                {
                    "candidate_index": i + 1,
                    "overall_score": sim_score,
                    "complementary_score": sim_score,
                    "match_type": "complementary",
                    "explanation": "Match based on profile similarity.",
                    "shared_context": {},
                }
                for i, (_, sim_score) in enumerate(candidates)
            ]

        return ranked

    # ── Full Pipeline ───────────────────────────────────────────────────

    async def generate_matches_for_attendee(
        self, attendee_id: uuid.UUID, top_k: int = 10
    ) -> list[Match]:
        """Run full 3-stage pipeline for a single attendee."""
        attendee = await self.db.get(Attendee, attendee_id)
        if not attendee:
            raise ValueError(f"Attendee {attendee_id} not found")

        # Stage 1: Ensure attendee is processed
        if attendee.embedding is None:
            attendee = await self.process_attendee(attendee)

        # Stage 2: Retrieve candidates
        candidates = await self.retrieve_candidates(attendee, top_k=top_k)
        if not candidates:
            return []

        # Stage 3: Rank & explain
        ranked = await self.rank_and_explain(attendee, candidates)

        # Persist matches
        matches = []
        for entry in ranked:
            idx = entry["candidate_index"] - 1
            if idx < 0 or idx >= len(candidates):
                continue
            candidate, sim_score = candidates[idx]

            match = Match(
                attendee_a_id=attendee.id,
                attendee_b_id=candidate.id,
                similarity_score=sim_score,
                complementary_score=entry.get("complementary_score", sim_score),
                overall_score=entry.get("overall_score", sim_score),
                match_type=entry.get("match_type", "complementary"),
                explanation=entry.get("explanation", ""),
                shared_context=entry.get("shared_context", {}),
            )
            self.db.add(match)
            matches.append(match)

        await self.db.commit()
        return matches

    async def generate_all_matches(self, top_k: int = 10) -> int:
        """Generate matches for all attendees."""
        result = await self.db.execute(select(Attendee))
        attendees = result.scalars().all()

        # First ensure all attendees are processed
        await self.process_all_attendees()

        total = 0
        for attendee in attendees:
            matches = await self.generate_matches_for_attendee(attendee.id, top_k)
            total += len(matches)

        return total
