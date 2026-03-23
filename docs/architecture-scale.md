# Architecture & Scale — POT Matchmaker

**How the system scales from 38 test profiles to 2,500 production attendees without fundamental redesign.**

---

## Pipeline Architecture

The matchmaking engine uses a **3-stage pipeline** designed to avoid the O(N²) problem of comparing every pair of attendees:

```
┌─────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  Stage 1:   │    │    Stage 2:      │    │    Stage 3:        │
│  EMBED      │───▶│    RETRIEVE      │───▶│    RANK & EXPLAIN  │
│  (per user) │    │  (per user, DB)  │    │  (per user, LLM)   │
└─────────────┘    └──────────────────┘    └────────────────────┘
```

### Stage 1 — Embed (one-time per attendee, on registration)

Each attendee's composite profile (name, title, company, goals, interests, AI summary, enriched data, vertical_tags, intent_tags) is:

1. Summarised by **GPT-4o** into a structured AI summary
2. Classified into **intent_tags** (10-tag taxonomy: deploying_capital, raising_capital, etc.)
3. Classified into **vertical_tags** (11-sector taxonomy: tokenisation, DeFi, infrastructure, etc.)
4. Embedded into a **1536-dimensional vector** via `text-embedding-3-small`
5. Stored in **PostgreSQL + pgvector**

**Cost**: 4 API calls per attendee. Runs once on registration + when profile changes.

### Stage 2 — Retrieve (per attendee, database-only)

For each attendee, the top candidates are retrieved using **pgvector's cosine distance operator** (`<=>`):

```sql
SELECT id, name, embedding <=> :query_embedding AS distance
FROM attendees
WHERE embedding IS NOT NULL AND id != :attendee_id
ORDER BY distance ASC
LIMIT :retrieval_limit    -- top_k * 5 = 50 candidates
```

Candidates are filtered through **hard constraints** (geography, seeking preferences, deal-stage compatibility) and reduced to **top_k = 10**.

**Cost**: Zero API calls. Pure database query using pgvector's IVFFlat index. Returns in < 50ms for 2,500 profiles.

### Stage 3 — Rank & Explain (per attendee, 1 LLM call)

The 10 shortlisted candidates are sent to **GPT-4o** in a single prompt. The model:

1. Re-ranks candidates considering **complementarity** (not just similarity)
2. Identifies **non-obvious connections** (different sectors solving the same problem)
3. Assesses **deal-readiness** (both parties in a position to transact)
4. Generates a **2–3 sentence explanation** per match
5. Returns structured JSON: `{ score, match_type, explanation, action_items }`

A **deterministic reranking layer** then applies cross-sector boosts from the `COMPLEMENTARY_VERTICALS` map (e.g., regulators + infrastructure builders get +0.10).

**Cost**: 1 GPT-4o call per attendee per pipeline run.

---

## Scaling Profile: 38 → 2,500

| Metric | Current (38) | Production (2,500) | Growth Factor |
|--------|-------------|-------------------|--------------|
| Embedding storage | ~58 KB vectors | ~3.8 MB vectors | 66× |
| pgvector retrieval per attendee | < 10ms | < 50ms (IVFFlat) | Sublinear |
| GPT-4o calls per full pipeline run | 38 | 2,500 | 66× (linear) |
| Total matches (at ~3.7/person) | 140 | ~9,250 | 66× |
| Full pipeline wall time | ~2 min | ~30 min (batched) | Bounded |

### Why this scales without redesign

1. **pgvector handles the heavy lifting.** The embedding retrieval step (Stage 2) is the only operation that touches all N profiles. pgvector's IVFFlat index keeps this sublinear — query time grows with `sqrt(N)`, not `N`. At 2,500 profiles, retrieval stays under 50ms per attendee.

2. **GPT-4o calls scale linearly, not quadratically.** Without the 3-stage approach, comparing all pairs would require N²/2 = 3.1M LLM calls. Our pipeline needs only N = 2,500 calls (one per attendee), each scoring 10 candidates.

3. **Pipeline is already batched and async.** `generate_all_matches()` processes attendees in a loop with async GPT-4o calls. Adding concurrency (e.g., `asyncio.Semaphore(10)`) would parallelize the 2,500 calls across 10 concurrent workers → ~25 min total.

4. **Enrichment is fire-and-forget.** Data enrichment (LinkedIn, Twitter, web scraping) runs as background jobs. It's already decoupled from the matching pipeline and can be parallelised independently.

5. **Daily cron is already in place.** The `02:00 UTC` scheduled job re-runs the full pipeline, ensuring new registrations get matches by morning.

### Infrastructure at scale

| Component | Current | At 2,500 | Action needed |
|-----------|---------|----------|--------------|
| **EC2** | t3.small (2 vCPU, 2 GB) | t3.medium (2 vCPU, 4 GB) | Upgrade if memory pressure during batch |
| **RDS PostgreSQL** | db.t3.micro | db.t3.small | Upgrade for concurrent pgvector queries |
| **pgvector index** | Default (brute force) | IVFFlat (lists=50) | Create index: `CREATE INDEX ON attendees USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)` |
| **OpenAI API** | Tier 1 | Tier 2+ (higher rate limits) | Top up credits; request rate limit increase |
| **SES** | Sandbox | Production access | Already requested (case #177412752700989) |

### Bottleneck analysis

| Bottleneck | Risk | Mitigation |
|------------|------|-----------|
| OpenAI rate limits | GPT-4o default: 500 RPM | Batch with 3s delays; or use `gpt-4o-mini` for summaries/classification (3× faster, 60% cheaper) |
| Memory during batch | 2,500 profiles + embeddings in memory | Stream results; process in batches of 100 (already configured via `MATCH_BATCH_SIZE`) |
| Database connections | Async pool exhaustion | SQLAlchemy pool_size=10 handles this; increase if needed |
| Email delivery | SES sandbox limitation | Production access resolves this (pending) |

---

## Pipeline Run Estimates (2,500 attendees)

### One-time onboarding (all 2,500 attendees)

| Stage | API Calls | Estimated Time |
|-------|-----------|---------------|
| AI Summaries (GPT-4o) | 2,500 | ~12 min (at 200 RPM) |
| Intent classification (GPT-4o) | 2,500 | ~12 min |
| Vertical classification (GPT-4o) | 2,500 | ~12 min |
| Embeddings (text-embedding-3-small) | 2,500 | ~3 min (at 1000 RPM) |
| **Total onboarding** | **10,000** | **~40 min** |

### Daily match refresh

| Stage | API Calls | Estimated Time |
|-------|-----------|---------------|
| pgvector retrieval | 0 (DB only) | < 2 min |
| GPT-4o rank & explain | 2,500 | ~12 min |
| **Total daily** | **2,500** | **~15 min** |

---

## Conclusion

The architecture is designed for exactly this scale. The 3-stage pipeline eliminates the N² problem, pgvector handles retrieval efficiently, and GPT-4o is only called for the final ranking step. Moving from 38 to 2,500 attendees requires:

1. A pgvector IVFFlat index (one SQL command)
2. A modest EC2/RDS upgrade
3. OpenAI Tier 2 rate limits
4. SES production access (already requested)

No database schema changes, no code changes, no architectural redesign required.
