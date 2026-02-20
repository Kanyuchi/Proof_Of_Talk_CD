import json
import uuid
from sqlalchemy import select, text, delete as sql_delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.models.attendee import Attendee, Match
from app.models.user import User
from app.services.embeddings import embed_attendee, generate_ai_summary, classify_intents

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Only persist matches above this quality threshold — avoids padding with weak connections
MIN_MATCH_SCORE = 0.60


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
        # Exclude admin-linked attendees so organisers never appear as recommendations
        query = text("""
            SELECT id, 1 - (embedding <=> :embedding) as similarity
            FROM attendees
            WHERE id != :attendee_id
              AND embedding IS NOT NULL
              AND id NOT IN (
                SELECT attendee_id FROM users
                WHERE is_admin = true AND attendee_id IS NOT NULL
              )
            ORDER BY embedding <=> :embedding
            LIMIT :top_k
        """)

        # Format embedding as pgvector-compatible string: [0.1,0.2,...]
        emb = attendee.embedding
        if hasattr(emb, 'tolist'):
            emb = emb.tolist()
        emb_str = "[" + ",".join(str(v) for v in emb) + "]"

        result = await self.db.execute(
            query,
            {
                "embedding": emb_str,
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
1. **Complementary matches** — one party has exactly what the other needs within the same or adjacent sector (investor meets startup in their thesis; regulator meets builder in their jurisdiction; capital deployer meets capital raiser)
2. **Non-obvious connections** — participants from CLEARLY DIFFERENT sectors who share an underlying common problem they'd uniquely benefit from solving together. Do NOT classify as non_obvious if both parties work in related or overlapping sectors — that is complementary.
3. **Deal-ready pairs** — both parties have explicit, active deal signals (deploying_capital + raising_capital; seeking_customers + has_product). Must be transactable at this event, not just networking.

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
  "overall_score": <0.0-1.0 — be conservative: only score above 0.75 if the connection is genuinely strong and specific. A score below 0.60 means the match adds little value.>,
  "complementary_score": <0.0-1.0>,
  "match_type": "complementary" | "non_obvious" | "deal_ready",
  "explanation": "<2-3 sentences explaining WHY these two should meet. Be specific about the mutual value. Reference concrete details like funding amounts, products, mandates, and the conference context.>",
  "shared_context": {{
    "sectors": ["list of shared/overlapping sectors"],
    "synergies": ["specific synergy points — be concrete, not generic"],
    "action_items": ["2-3 specific conversation topics or deal scenarios to explore at POT 2026"]
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
            raw = response.choices[0].message.content.strip()
            # Strip markdown code fences if GPT wraps response
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            ranked = json.loads(raw)
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
        self, attendee_id: uuid.UUID, top_k: int = 10, clear_existing: bool = True
    ) -> list[Match]:
        """Run full 3-stage pipeline for a single attendee.

        Args:
            clear_existing: When True (single-attendee call), removes all existing
                matches involving this attendee before regenerating. When False
                (batch call), relies on the caller to have cleared matches upfront.
        """
        attendee = await self.db.get(Attendee, attendee_id)
        if not attendee:
            raise ValueError(f"Attendee {attendee_id} not found")

        # Stage 1: Ensure attendee is processed
        if attendee.embedding is None:
            attendee = await self.process_attendee(attendee)

        # Clear stale matches for this attendee (both directions) when called individually
        if clear_existing:
            await self.db.execute(
                sql_delete(Match).where(
                    or_(
                        Match.attendee_a_id == attendee_id,
                        Match.attendee_b_id == attendee_id,
                    )
                )
            )
            await self.db.commit()

        # Stage 2: Retrieve candidates
        candidates = await self.retrieve_candidates(attendee, top_k=top_k)
        if not candidates:
            return []

        # Stage 3: Rank & explain
        ranked = await self.rank_and_explain(attendee, candidates)

        # Persist matches — with deduplication and score threshold
        matches = []
        for entry in ranked:
            idx = entry["candidate_index"] - 1
            if idx < 0 or idx >= len(candidates):
                continue
            candidate, sim_score = candidates[idx]

            # Apply minimum quality threshold — avoid padding with weak matches
            overall_score = entry.get("overall_score", sim_score)
            if overall_score < MIN_MATCH_SCORE:
                continue

            # Deduplication: skip if this pair already exists in either direction
            existing = (
                await self.db.execute(
                    select(Match).where(
                        or_(
                            (Match.attendee_a_id == attendee.id)
                            & (Match.attendee_b_id == candidate.id),
                            (Match.attendee_a_id == candidate.id)
                            & (Match.attendee_b_id == attendee.id),
                        )
                    )
                )
            ).scalars().first()
            if existing:
                continue

            match = Match(
                attendee_a_id=attendee.id,
                attendee_b_id=candidate.id,
                similarity_score=sim_score,
                complementary_score=entry.get("complementary_score", sim_score),
                overall_score=overall_score,
                match_type=entry.get("match_type", "complementary"),
                explanation=entry.get("explanation", ""),
                shared_context=entry.get("shared_context", {}),
            )
            self.db.add(match)
            matches.append(match)

        await self.db.commit()
        return matches

    async def generate_all_matches(self, top_k: int = 10) -> int:
        """Generate matches for all attendees.

        Wipes existing matches first so reruns produce a clean, deduplicated result.
        Each pair (A, B) produces exactly one Match record — whichever attendee is
        processed first becomes attendee_a.
        """
        # Start clean — prevents duplicates on reruns
        await self.db.execute(sql_delete(Match))
        await self.db.commit()

        # Exclude admin-linked attendees from the matching pool entirely
        admin_ids_subq = select(User.attendee_id).where(
            User.is_admin.is_(True),
            User.attendee_id.isnot(None),
        )
        result = await self.db.execute(
            select(Attendee).where(~Attendee.id.in_(admin_ids_subq))
        )
        attendees = result.scalars().all()

        # Ensure all attendees have embeddings / AI summaries
        await self.process_all_attendees()

        total = 0
        for attendee in attendees:
            # clear_existing=False because we wiped above and use dedup check
            matches = await self.generate_matches_for_attendee(
                attendee.id, top_k, clear_existing=False
            )
            total += len(matches)

        return total


async def run_matching_pipeline(db: AsyncSession, top_k: int = 10) -> int:
    """Run the full matching pipeline and return generated match count."""
    engine = MatchingEngine(db)
    return await engine.generate_all_matches(top_k=top_k)
