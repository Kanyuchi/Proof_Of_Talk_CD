# What's Next — backend

> Tied to goal: AI matchmaking engine for Proof of Talk 2026

## Now (immediate next steps)
1. [launch] Continue welcome waves — 261 sent / 462 eligible remaining (~100/day from warm team@xventures.de via `send_welcome_batch.py --limit 100 --confirm`)
2. [launch] EMAIL_MODE=all flip is now UNBLOCKED (self-recovery solved + blast footgun guarded). Pure launch decision — flip when ready to turn on all automated email (match intros, mutual/meeting alerts).
3. Confirm attendee count with Chiara (email drafted — 24 valid from Extasy API)
3. Verify frontend at meet.proofoftalk.io shows vertical_tags in attendee profiles
4. Re-generate matches using vertical_tags as a matching signal (improve match quality)

## Soon
- Automate daily Extasy → RDS → Supabase sync
- Add LinkedIn/Twitter URLs for Extasy attendees (enrichment sources currently empty)

## Later / Backlog
- Retire RDS once Supabase confirmed as sole production DB
- Supabase Edge Functions for real-time match notifications

## Done ✓
- [sync] All Sync Health errors + partials fixed (commit 8293c9b) AND smoke-tested green on prod (20e8026): all 4 jobs flipped sync_status to ok — match_refresh (32 matches), speakers (errors 1→0), extasy (errors 58→0), grid_audit (terminal INSERT persisted). connection-drop retry (run_with_db_retry); extasy mis-count fixed + error_reasons persisted; speaker dup-row collision handled. (2026-05-21)
- [matching] Bulk-rebuild blast guard: `generate_all_matches` passes `notify=False` so a full rebuild can't email ~739 intros — unblocks EMAIL_MODE=all (commit 85b41d3) (2026-05-21)
- [launch] Welcome wave 3 sent: 100/100, 0 failed (261 total sent / 462 remaining) (2026-05-21)
- [matches] Fixed `/pending-count` 422 (route shadowing by `/{attendee_id}`) — DEPLOYED + verified on prod (commit fbfd954, Railway 149906df) (2026-05-21)
- [auth] forgot-password self-recovery DEPLOYED (commit 3c303de, Railway c8a80f7c) — unclaimed attendees get a force-sent magic-link claim email; EMAIL_MODE stays allowlist so bulk triggers remain gated (2026-05-21)
- [launch] Welcome wave 2 sent: 100/100, 0 failed; Mauricio Magaldi Suguihura included (2026-05-21)
- [auth] forgot-password no longer dead-ends the 700 unclaimed attendees — falls back to magic-link claim email; resent Tommi Vuorenmaa's welcome (2026-05-21)
- Project files bootstrapped (2026-03-19)
- Include complimentary (REDEEMED) tickets in Extasy pipeline (2026-03-19)
- Deploy updated code to green EC2 (2026-03-19)
- Enrich + match Pierre Kaklamanos — 8 matches generated (2026-03-19)
- OpenAI API key confirmed working on EC2 (2026-03-19)
- Created Supabase tables (attendees, matches, users) (2026-03-19)
- Full RDS → Supabase sync: 38 attendees, 129 matches, all enrichment data (2026-03-19)
- Added vertical_tags — 11 1000minds sector verticals, 38/38 attendees classified (2026-03-19)
