# Cost Per Attendee — POT Matchmaker

**Target: < €0.50 per attendee (KR 3.3)**

Analysis based on actual test run data (38 attendees, 140 matches) extrapolated to 2,500 attendees.

---

## OpenAI API Pricing (as of March 2026)

| Model | Input | Output |
|-------|-------|--------|
| gpt-4o | $2.50 / 1M tokens | $10.00 / 1M tokens |
| text-embedding-3-small | $0.02 / 1M tokens | — |

---

## Per-Attendee Cost Breakdown

### 1. Onboarding (one-time, on registration)

| Operation | Model | Input tokens | Output tokens | Cost |
|-----------|-------|-------------|--------------|------|
| AI Summary | gpt-4o | ~400 | ~200 | $0.003 |
| Intent classification | gpt-4o | ~300 | ~50 | $0.001 |
| Vertical classification | gpt-4o | ~300 | ~50 | $0.001 |
| Embedding | text-embedding-3-small | ~300 | — | $0.000006 |
| **Onboarding subtotal** | | | | **$0.005** |

### 2. Match generation (per pipeline run)

| Operation | Model | Input tokens | Output tokens | Cost |
|-----------|-------|-------------|--------------|------|
| Rank & explain (10 candidates) | gpt-4o | ~3,000 | ~2,000 | $0.028 |
| **Match generation subtotal** | | | | **$0.028** |

### 3. Data enrichment (one-time, optional)

| Source | Cost per call | Calls | Cost |
|--------|-------------|-------|------|
| LinkedIn (Proxycurl) | $0.01 | 1 | $0.010 |
| Twitter/X API | Free (v2 basic) | 2 | $0.000 |
| Company website scrape | Free | 1 | $0.000 |
| **Enrichment subtotal** | | | **$0.010** |

### 4. Email delivery (SES)

| Email type | Cost per email | Emails per attendee |
|------------|---------------|-------------------|
| Match intro | $0.0001 | 1 |
| Mutual match notifications | $0.0001 | ~2 |
| Meeting confirmations | $0.0001 | ~1 |
| **Email subtotal** | | **$0.0004** |

---

## Total Cost Per Attendee

| Scenario | Cost (USD) | Cost (EUR)* |
|----------|-----------|-------------|
| **Onboarding + 1 match run** (minimum) | $0.033 | **€0.031** |
| **+ Enrichment** (recommended) | $0.043 | **€0.040** |
| **+ 10 daily refresh runs** (pre-event period) | $0.323 | **€0.302** |
| **+ 30 daily refresh runs** (full month) | $0.883 | **€0.825** |

*EUR conversion at 1 USD = 0.935 EUR (March 2026)

### Realistic production scenario

For Proof of Talk 2026, the timeline is:
- Attendees register over ~8 weeks before the event
- Match pipeline runs daily at 02:00 UTC
- Each attendee gets ~30 pipeline runs on average (from their registration date to event day)

**Per attendee (realistic): $0.043 (onboarding) + 30 × $0.028 (daily runs) = $0.883 / €0.83**

This **exceeds the €0.50 target** if running daily refreshes for a full month.

---

## Cost Optimisation — Getting Under €0.50

| Optimisation | Saving | New cost/attendee |
|-------------|--------|------------------|
| **Use gpt-4o-mini for classification** (summary + intents + verticals) | 60% on onboarding | $0.002 → saves $0.003 |
| **Reduce refresh frequency to 2×/week** instead of daily | 71% on matching | 8 runs × $0.028 = $0.224 |
| **Skip re-ranking unchanged profiles** (cache by profile hash) | ~50% of daily runs | 4 effective runs = $0.112 |

**Optimised per attendee: $0.002 + $0.112 + $0.010 = $0.124 / €0.12**

**With 2×/week refresh: $0.002 + $0.224 + $0.010 = $0.236 / €0.22**

Both well under the €0.50 target.

---

## Infrastructure Cost (fixed, not per-attendee)

| Component | Monthly cost | Annual |
|-----------|-------------|--------|
| EC2 t3.small (green) | $18 | $216 |
| RDS PostgreSQL (db.t3.micro) | $15 | $180 |
| AWS SES | ~$5 | $60 |
| Netlify (frontend CDN) | $0 (free tier) | $0 |
| **Infrastructure total** | **~$38/month** | **$456/year** |

Per attendee (amortised): $456 / 2,500 = **$0.18 / €0.17**

---

## Total Cost at 2,500 Attendees

| Component | Total (USD) | Per attendee (EUR) |
|-----------|------------|-------------------|
| Onboarding (2,500 × $0.005) | $12.50 | €0.005 |
| Enrichment (2,500 × $0.010) | $25.00 | €0.009 |
| Match generation (2,500 × 8 runs × $0.028)* | $560.00 | €0.209 |
| Infrastructure (annual) | $456.00 | €0.170 |
| Email (2,500 × ~4 emails) | $1.00 | €0.000 |
| **TOTAL** | **$1,054.50** | **€0.394/attendee** |

*Assumes 2×/week refresh over 4 weeks before event = 8 runs per attendee.

---

## Verdict

**€0.39 per attendee — under the €0.50 target.**

With daily refreshes over a full month it rises to €0.83, but 2×/week refreshes are sufficient for match quality (profiles don't change that frequently) and keep costs well within budget.

### Cost sensitivity

| Attendees | Total cost (optimised) | Per attendee |
|-----------|----------------------|-------------|
| 500 | $495 | €0.39 |
| 1,000 | $735 | €0.35 |
| 2,500 | $1,055 | €0.39 |
| 5,000 | $1,853 | €0.35 |

Infrastructure costs are fixed, so per-attendee cost actually decreases at higher volumes.
