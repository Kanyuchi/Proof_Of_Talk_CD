import json
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text, delete as sql_delete, or_, and_
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

# Cross-sector verticals that create high-value complementary matches
COMPLEMENTARY_VERTICALS = {
    "policy_regulation_macro": ["infrastructure_and_scaling", "tokenisation_of_finance", "decentralized_finance", "privacy"],
    "tokenisation_of_finance": ["investment_and_capital_markets", "policy_regulation_macro", "infrastructure_and_scaling"],
    "infrastructure_and_scaling": ["decentralized_finance", "policy_regulation_macro", "ai_depin_frontier_tech", "privacy"],
    "investment_and_capital_markets": ["tokenisation_of_finance", "decentralized_finance", "bitcoin"],
    "decentralized_finance": ["infrastructure_and_scaling", "policy_regulation_macro", "tokenisation_of_finance", "privacy"],
    "ai_depin_frontier_tech": ["infrastructure_and_scaling", "decentralized_ai", "ecosystem_and_foundations"],
    "decentralized_ai": ["ai_depin_frontier_tech", "infrastructure_and_scaling"],
    "bitcoin": ["investment_and_capital_markets", "infrastructure_and_scaling"],
    "ecosystem_and_foundations": ["infrastructure_and_scaling", "ai_depin_frontier_tech", "culture_media_gaming"],
    "culture_media_gaming": ["ecosystem_and_foundations", "decentralized_finance"],
    "prediction_markets": ["decentralized_finance", "ai_depin_frontier_tech"],
    "privacy": ["infrastructure_and_scaling", "decentralized_finance", "policy_regulation_macro"],
}

# Map Grid B2B sectors → our vertical taxonomy so Grid intelligence feeds into
# complementarity scoring.  Grid sector names come from thegrid.id/profiles.
GRID_SECTOR_TO_VERTICALS: dict[str, list[str]] = {
    "blockchain platforms":        ["infrastructure_and_scaling"],
    "infrastructure":              ["infrastructure_and_scaling"],
    "finance":                     ["decentralized_finance", "investment_and_capital_markets"],
    "custody and wallets":         ["infrastructure_and_scaling", "tokenisation_of_finance"],
    "payments":                    ["tokenisation_of_finance", "decentralized_finance"],
    "security":                    ["infrastructure_and_scaling", "privacy"],
    "data & analytics":            ["ai_depin_frontier_tech", "infrastructure_and_scaling"],
    "gaming":                      ["culture_media_gaming"],
    "nft":                         ["culture_media_gaming"],
    "defi":                        ["decentralized_finance"],
    "dao":                         ["ecosystem_and_foundations"],
    "identity":                    ["privacy", "infrastructure_and_scaling"],
    "social":                      ["culture_media_gaming", "ecosystem_and_foundations"],
    "exchange":                    ["decentralized_finance", "investment_and_capital_markets"],
    "stablecoin":                  ["tokenisation_of_finance", "decentralized_finance"],
    "lending":                     ["decentralized_finance"],
    "mining":                      ["bitcoin"],
    "ai":                          ["decentralized_ai", "ai_depin_frontier_tech"],
    "regulation":                  ["policy_regulation_macro"],
}


def _grid_verticals(attendee: Attendee) -> set[str]:
    """Extract our vertical tags from an attendee's Grid sector data."""
    grid = (attendee.enriched_profile or {}).get("grid") or {}
    sector = (grid.get("grid_sector") or "").strip().lower()
    if not sector:
        return set()
    return set(GRID_SECTOR_TO_VERTICALS.get(sector, []))


def _grid_context(attendee: Attendee) -> str:
    """Build a concise Grid intelligence summary for GPT-4o candidate descriptions."""
    grid = (attendee.enriched_profile or {}).get("grid") or {}
    if not grid.get("grid_name"):
        return ""
    parts = []
    if grid.get("grid_description"):
        parts.append(f"Grid Verified: {grid['grid_description']}")
    if grid.get("grid_sector"):
        parts.append(f"Grid Sector: {grid['grid_sector']}")
    if grid.get("grid_type"):
        parts.append(f"Company Type: {grid['grid_type']}")
    products = grid.get("grid_products") or []
    main_products = [p for p in products if p.get("is_main")] or products[:2]
    if main_products:
        names = [p["name"] for p in main_products if p.get("name")]
        if names:
            parts.append(f"Key Products: {', '.join(names)}")
    return "\n  ".join(parts)


class MatchingEngine:
    """3-stage AI matchmaking pipeline: Embed -> Retrieve -> Rank & Explain."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._candidate_cache: dict[str, dict] = {}

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

    @staticmethod
    def _norm_set(values: list[str] | None) -> set[str]:
        return {
            str(v).strip().lower()
            for v in (values or [])
            if str(v).strip()
        }

    @staticmethod
    def _deal_stage_compatible(stage_a: str | None, stage_b: str | None) -> bool:
        if not stage_a or not stage_b:
            return True
        a = stage_a.strip().lower()
        b = stage_b.strip().lower()
        if a == b:
            return True
        if a in {"any", "all", "global"} or b in {"any", "all", "global"}:
            return True
        if "series" in a and "series" in b:
            return True
        if "growth" in {a, b} and ("series" in a or "series" in b):
            return True
        # Keep policy-focused attendees constrained unless explicit overlap exists
        if "policy" in {a, b}:
            return False
        return False

    def _is_candidate_eligible(self, attendee: Attendee, candidate: Attendee) -> bool:
        # Respect each side's explicit exclusions.
        attendee_exclusions = self._norm_set(getattr(attendee, "not_looking_for", []))
        candidate_exclusions = self._norm_set(getattr(candidate, "not_looking_for", []))
        candidate_ticket = str(candidate.ticket_type.value if hasattr(candidate.ticket_type, "value") else candidate.ticket_type).lower()
        attendee_ticket = str(attendee.ticket_type.value if hasattr(attendee.ticket_type, "value") else attendee.ticket_type).lower()
        if candidate_ticket in attendee_exclusions:
            return False
        if attendee_ticket in candidate_exclusions:
            return False

        # If both sides specified preferred geographies, they must intersect.
        attendee_geos = self._norm_set(getattr(attendee, "preferred_geographies", []))
        candidate_geos = self._norm_set(getattr(candidate, "preferred_geographies", []))
        if attendee_geos and candidate_geos and attendee_geos.isdisjoint(candidate_geos):
            return False

        # Deal-stage compatibility as a hard filter.
        if not self._deal_stage_compatible(
            getattr(attendee, "deal_stage", None),
            getattr(candidate, "deal_stage", None),
        ):
            return False

        # "Seeking" constraints: at least one target signal should match when provided.
        attendee_seeking = self._norm_set(getattr(attendee, "seeking", []))
        candidate_signals = self._norm_set(getattr(candidate, "intent_tags", []))
        candidate_signals.add(candidate_ticket)
        candidate_stage = getattr(candidate, "deal_stage", None)
        if candidate_stage:
            candidate_signals.add(candidate_stage.strip().lower())
        if attendee_seeking and attendee_seeking.isdisjoint(candidate_signals):
            return False

        candidate_seeking = self._norm_set(getattr(candidate, "seeking", []))
        attendee_signals = self._norm_set(getattr(attendee, "intent_tags", []))
        attendee_signals.add(attendee_ticket)
        attendee_stage = getattr(attendee, "deal_stage", None)
        if attendee_stage:
            attendee_signals.add(attendee_stage.strip().lower())
        if candidate_seeking and candidate_seeking.isdisjoint(attendee_signals):
            return False

        return True

    async def retrieve_candidates(
        self, attendee: Attendee, top_k: int = 10
    ) -> list[tuple[Attendee, float]]:
        """Find top-K most similar attendees using pgvector cosine distance."""
        if attendee.embedding is None:
            attendee = await self.process_attendee(attendee)

        cache_key = str(attendee.id)
        cached = self._candidate_cache.get(cache_key)
        if cached and cached.get("expires_at", datetime.min.replace(tzinfo=timezone.utc)) > datetime.now(timezone.utc):
            hydrated: list[tuple[Attendee, float]] = []
            for item in cached.get("items", []):
                candidate = await self.db.get(Attendee, item["id"])
                if candidate and self._is_candidate_eligible(attendee, candidate):
                    hydrated.append((candidate, float(item["similarity"])))
                    if len(hydrated) >= top_k:
                        break
            if hydrated:
                return hydrated

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

        retrieval_limit = max(top_k * 5, top_k)
        result = await self.db.execute(
            query,
            {
                "embedding": emb_str,
                "attendee_id": str(attendee.id),
                "top_k": retrieval_limit,
            },
        )
        rows = result.fetchall()

        candidates = []
        for row in rows:
            candidate = await self.db.get(Attendee, row.id)
            if candidate and self._is_candidate_eligible(attendee, candidate):
                candidates.append((candidate, float(row.similarity)))
                if len(candidates) >= top_k:
                    break

        # Cache raw candidates for future calls in this pipeline window
        self._candidate_cache[cache_key] = {
            "items": [{"id": c.id, "similarity": s} for c, s in candidates],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=6),
        }

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

        # Fetch prior decline reasons for feedback loop
        decline_feedback = ""
        try:
            declined = await self.db.execute(
                select(Match).where(
                    or_(
                        and_(Match.attendee_a_id == attendee.id, Match.status_a == "declined"),
                        and_(Match.attendee_b_id == attendee.id, Match.status_b == "declined"),
                    ),
                    Match.decline_reason.isnot(None),
                )
            )
            declined_matches = declined.scalars().all()
            if declined_matches:
                reasons = []
                for dm in declined_matches[:5]:  # cap at 5 to control prompt length
                    other_id = dm.attendee_b_id if dm.attendee_a_id == attendee.id else dm.attendee_a_id
                    other = await self.db.get(Attendee, other_id)
                    name = other.name if other else "Unknown"
                    reasons.append(f"- Declined {name}: {dm.decline_reason}")
                decline_feedback = (
                    "\n\nPRIOR FEEDBACK (matches this attendee declined and why — avoid similar matches):\n"
                    + "\n".join(reasons)
                )
        except Exception:
            pass  # Non-critical; proceed without feedback

        candidate_descriptions = []
        for i, (candidate, sim_score) in enumerate(candidates):
            grid_info = _grid_context(candidate)
            candidate_descriptions.append(
                f"Candidate {i+1}:\n"
                f"  Name: {candidate.name}\n"
                f"  Title: {candidate.title}\n"
                f"  Company: {candidate.company}\n"
                f"  Goals: {candidate.goals or 'Not specified'}\n"
                f"  Interests: {', '.join(candidate.interests) if candidate.interests else 'Not specified'}\n"
                f"  AI Summary: {candidate.ai_summary or 'Not available'}\n"
                f"  Intent Tags: {', '.join(candidate.intent_tags) if candidate.intent_tags else 'Not classified'}\n"
                f"  Vertical Tags: {', '.join(candidate.vertical_tags) if candidate.vertical_tags else 'Not classified'}\n"
                f"  Deal Readiness: {candidate.deal_readiness_score or 0:.2f}\n"
                f"  Vector Similarity: {sim_score:.3f}"
                + (f"\n  {grid_info}" if grid_info else "")
            )

        prompt = f"""You are the AI matchmaking engine for Proof of Talk 2026, an exclusive Web3 conference at the Louvre Palace with 2,500 decision-makers controlling $18 trillion in assets.

Your task: Re-rank and explain match recommendations for the attendee below. Go beyond surface-level keyword matching. Find:
1. **Complementary matches** — one party has exactly what the other needs within the same or adjacent sector (investor meets startup in their thesis; regulator meets builder in their jurisdiction; capital deployer meets capital raiser)
2. **Non-obvious connections** — participants from CLEARLY DIFFERENT sectors who share an underlying common problem they'd uniquely benefit from solving together. Do NOT classify as non_obvious if both parties work in related or overlapping sectors — that is complementary.
3. **Deal-ready pairs** — both parties have explicit, active deal signals (deploying_capital + raising_capital; seeking_customers + has_product). Must be transactable at this event, not just networking.

Consider sector verticals when assessing complementarity. Cross-sector matches between complementary verticals (e.g., policy + infrastructure, tokenisation + investment) often create higher value than same-sector matches.

When "Grid Verified" company data is present, treat it as the most authoritative source for what a company does, its products, and its sector. Use Grid products to identify concrete supply/demand fits (e.g., a custody product matches an investor needing custody; a compliance module matches a regulated entity). Grid sector alignment or complementarity should boost match confidence.

TARGET ATTENDEE:
Name: {attendee.name}
Title: {attendee.title}
Company: {attendee.company}
Goals: {attendee.goals or 'Not specified'}
Who they want to meet: {attendee.target_companies or 'Not specified'}
Interests: {', '.join(attendee.interests) if attendee.interests else 'Not specified'}
AI Summary: {attendee.ai_summary or 'Not available'}
Intent Tags: {', '.join(attendee.intent_tags) if attendee.intent_tags else 'Not classified'}
Vertical Tags: {', '.join(attendee.vertical_tags) if attendee.vertical_tags else 'Not classified'}
Deal Readiness: {attendee.deal_readiness_score or 0:.2f}
{_grid_context(attendee)}

IMPORTANT: If the attendee specified companies/people they want to meet, give HIGHEST PRIORITY to candidates from those companies or similar companies. This is explicit user intent and overrides AI inference.
{decline_feedback}
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
            model=settings.OPENAI_RERANK_MODEL or settings.OPENAI_CHAT_MODEL,
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
                    "explanation_confidence": sim_score,
                }
                for i, (_, sim_score) in enumerate(candidates)
            ]

        # Deterministic rerank for diversity/novelty and duplicate-topic suppression
        if settings.AI_RERANK_ENABLED:
            ranked = self._deterministic_rerank(ranked, attendee, candidates)

        if settings.AI_CONFIDENCE_ENABLED:
            for entry in ranked:
                entry["explanation_confidence"] = self._estimate_explanation_confidence(entry)

        return ranked

    @staticmethod
    def _extract_primary_topic(entry: dict) -> str:
        context = entry.get("shared_context") or {}
        sectors = context.get("sectors") or []
        synergies = context.get("synergies") or []
        if sectors:
            return str(sectors[0]).strip().lower()
        if synergies:
            return str(synergies[0]).strip().lower()
        return "unknown"

    def _deterministic_rerank(self, ranked: list[dict], attendee: Attendee, candidates: list[tuple]) -> list[dict]:
        """Apply deterministic boosts/penalties after LLM ranking."""
        adjusted = []
        seen_topics = set()
        for entry in ranked:
            score = float(entry.get("overall_score", 0.0))
            match_type = str(entry.get("match_type", "complementary"))
            topic = self._extract_primary_topic(entry)

            # Small novelty boost for non-obvious cross-sector pairings.
            if match_type == "non_obvious":
                score += 0.03

            # Penalize repeated primary topics to reduce duplicate recommendations.
            if topic in seen_topics:
                score -= 0.05
            else:
                seen_topics.add(topic)

            # Vertical affinity boost — combine explicit tags + Grid sector intelligence
            idx = entry.get("candidate_index", 0) - 1
            if 0 <= idx < len(candidates):
                candidate = candidates[idx][0]
                # Merge explicit vertical_tags with Grid-derived verticals
                a_verts = set(attendee.vertical_tags or []) | _grid_verticals(attendee)
                c_verts = set(candidate.vertical_tags or []) | _grid_verticals(candidate)
                complementary_hit = any(
                    v in COMPLEMENTARY_VERTICALS.get(av, [])
                    for av in a_verts for v in c_verts
                )
                if complementary_hit:
                    score += 0.04
                elif a_verts & c_verts:
                    score += 0.02

                # Extra boost when Grid products suggest supply/demand fit
                a_grid = (attendee.enriched_profile or {}).get("grid") or {}
                c_grid = (candidate.enriched_profile or {}).get("grid") or {}
                if a_grid.get("grid_products") and c_grid.get("grid_products"):
                    score += 0.02  # both have verified product data = higher confidence

            entry["overall_score"] = max(0.0, min(1.0, score))
            adjusted.append(entry)

        adjusted.sort(key=lambda e: float(e.get("overall_score", 0.0)), reverse=True)
        return adjusted

    @staticmethod
    def _estimate_explanation_confidence(entry: dict) -> float:
        """Heuristic confidence score for explanation quality (0-1)."""
        overall = float(entry.get("overall_score", 0.0))
        comp = float(entry.get("complementary_score", 0.0))
        explanation = str(entry.get("explanation", "")).strip()
        context = entry.get("shared_context") or {}
        action_items = context.get("action_items") or []

        length_bonus = 0.08 if len(explanation) >= 120 else 0.03
        action_bonus = min(0.08, 0.03 * len(action_items))
        raw = (0.55 * overall) + (0.25 * comp) + length_bonus + action_bonus
        return max(0.0, min(1.0, raw))

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
                explanation_confidence=entry.get("explanation_confidence"),
            )
            self.db.add(match)
            matches.append(match)

        await self.db.commit()

        # Fire-and-forget: notify attendee of their top match via email
        if matches:
            try:
                from app.services.email import send_match_intro_email
                top = matches[0]
                top_candidate_id = (
                    top.attendee_b_id if top.attendee_a_id == attendee.id else top.attendee_a_id
                )
                top_candidate = await self.db.get(Attendee, top_candidate_id)
                if top_candidate and attendee.email:
                    # Respect privacy mode — show company name instead of personal name for b2b_only
                    if getattr(top_candidate, "privacy_mode", "full") == "b2b_only":
                        display_name = top_candidate.company or "Anonymous"
                        display_title = ""
                    else:
                        display_name = top_candidate.name
                        display_title = top_candidate.title or ""
                    send_match_intro_email(
                        to_email=attendee.email,
                        attendee_name=attendee.name,
                        match_name=display_name,
                        match_title=display_title,
                        match_company=top_candidate.company or "",
                        explanation=top.explanation or "",
                        match_count=len(matches),
                        magic_token=attendee.magic_access_token,
                    )
            except Exception as exc:  # noqa: BLE001
                import logging
                logging.getLogger(__name__).warning("Post-match email failed: %s", exc)

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

        # Candidate precompute cache to reduce repeated retrieval load in this run
        await self.precompute_candidate_cache(attendees, top_k=max(10, top_k))

        total = 0
        batch_size = max(1, settings.MATCH_BATCH_SIZE)
        for i in range(0, len(attendees), batch_size):
            batch = attendees[i : i + batch_size]
            for attendee in batch:
                # clear_existing=False because we wiped above and use dedup check
                matches = await self.generate_matches_for_attendee(
                    attendee.id, top_k, clear_existing=False
                )
                total += len(matches)
                # Explicit yield to keep event loop responsive under load.
                await asyncio.sleep(0)

        return total

    async def precompute_candidate_cache(self, attendees: list[Attendee], top_k: int = 10) -> None:
        """Precompute candidate retrieval cache for the current pipeline run."""
        for attendee in attendees:
            if attendee.embedding is None:
                continue
            await self.retrieve_candidates(attendee, top_k=top_k)


async def run_matching_pipeline(db: AsyncSession, top_k: int = 10) -> int:
    """Run the full matching pipeline and return generated match count."""
    engine = MatchingEngine(db)
    return await engine.generate_all_matches(top_k=top_k)
