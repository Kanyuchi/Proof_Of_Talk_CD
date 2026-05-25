# onboarding_video — POT Matchmaker "Getting Started" (REAL APP screen recording)

A ~60s onboarding film that is a **real Playwright screen recording of the
actual POT Matchmaker app** (React on :5173 + FastAPI on :8000, pointed at the
prod Supabase DB), driven through the real onboarding flow by a demo account.

> The earlier JSX-mock cut (`onboarding.jsx` / `app.jsx` / `animations.jsx` /
> `render.mjs` + the `pot_onboarding_1080p.mp4`) was **rejected** — it animated a
> mock UI, not the product. This pipeline records the real UI instead. The mock
> files are left in place for reference but are NOT used to build the deliverable.

## Deliverables

- `pot_onboarding_realapp_4k.mp4` — **TRUE 4K** 3840×2160, 30fps, ~64s, H.264
  (CRF 18) + AAC music bed. The crisp cut — built from high-DPI screenshot
  frames (see "4K pipeline" below). **This is the one to ship.**
- `pot_onboarding_realapp_1080p.mp4` — 1920×1080, 30fps, ~62.7s, H.264 + AAC.
  The original cut; left in place. It was captured at 1280×720 (Playwright
  `recordVideo`) then upscaled, so its UI text is soft.

Both are gitignored (heavy binaries) — regenerate with the scripts below.

## The flow recorded (real app, in order)

| Beat | Screen | What happens |
|------|--------|--------------|
| 1 | `/m/{token}?unlock=1` | Magic-link claim — type a password → "Create my account" → lands logged in |
| 2 | `/profile` | "Your write-up" → **Regenerate with AI** (real OpenAI call fills the textarea) → tweak a word → **Save** (green confirmation) |
| 3 | `/matches` | AI matches load, ranked → **Accept** ("I'd like to meet") a pending match |
| 4 | `/messages` | Open the pre-staged **mutual** thread (Thomas Weber) → type + send a message in the enabled composer |
| 5 | `/matches` | Booking — click a "Both free at — tap to book" slot chip → confirmed meeting (Louvre) |
| 6 | `/threads` | Open the demo "Tokenisation & RWA — Builders Circle" thread → type a reply |

## Pieces (all committed)

- `backend/scripts/stage_onboarding_video_demo.py` — stages the demo identity
  **Alex Rivera** (`alex.video@demo.proofoftalk.io`, DELEGATE, privacy=full) with
  goals+interests, a magic token, a real embedding, hand-built **demo-only**
  curated matches (one set MUTUAL → Thomas Weber), and a demo-only thread with
  seed posts. Everything is `@demo.proofoftalk.io` → excluded from all adoption/
  usage metrics + the concierge demo-scope keeps real attendees off camera.
  - `python scripts/stage_onboarding_video_demo.py` — full stage
  - `--matches-only` — rebuild just the demo matches (used mid-recording: the
    real profile-save fires `refresh_profile_matches`, which would otherwise
    replace the curated demo set with real-pool matches)
  - `--reset` — delete Alex's `users` row only (re-arm the claim/set-password flow)
- `record_realapp.mjs` — Playwright recorder. Re-stages, then drives all 6 beats
  in ONE `recordVideo` context (1280×720) → `raw/<auto>.webm`. Deliberate
  `waitForTimeout` pauses + `{delay}` typing so the viewer can read each screen.
- `assemble_realapp.sh` — ffmpeg: speeds raw ~1.25× → ~63s, scales to 1080p,
  burns a 2s "Getting started" intro + per-beat step captions, muxes
  `../our_version/music.mp3` at vol 0.2 (fade in/out). Output is the deliverable.

## 4K pipeline (the crisp cut — preferred)

Playwright's `recordVideo` rasterizes at the `size` param and **ignores
`deviceScaleFactor`**, so it can only capture 1280×720 → upscaling to 4K stays
soft. The 4K pipeline instead captures **high-DPI screenshot frames**:

> browser context `viewport: 1920×1080` + **`deviceScaleFactor: 2`** →
> `page.screenshot()` yields **3840×2160** sharp PNG/JPEG frames (crisp text,
> correct layout — a 3840 CSS viewport would shrink the UI; this keeps it
> normal-sized at 2× pixel density).

- `record_realapp_4k.mjs` — drives the SAME 6-beat flow + the SAME mid-run
  re-stage as `record_realapp.mjs`, but a background loop snaps 4K JPEG frames
  (q92, ~85ms each → ~10fps real) as fast as it can into `frames4k/`, recording
  each frame's real-time offset + per-beat markers into `frames4k/beats.json`.
- `assemble_realapp_4k.sh` — builds an ffmpeg **concat list** with per-frame
  durations from `beats.json` (so playback is TRUE real time — deliberate pauses
  stay pauses, typing stays smooth), re-times to a constant 30fps, scales the
  burned-in captions ~2× for 4K, muxes `../our_version/music.mp3` (vol 0.2, fade
  in/out). Output: `pot_onboarding_realapp_4k.mp4` (3840×2160, H.264 CRF 18).

```bash
# 1. servers (prod DB via backend/.env DATABASE_URL)
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000 --log-level warning &
cd frontend && npm run dev &        # serves :5173, proxies /api → :8000
# wait until: curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/dashboard/adoption  → 401

# 2. record 4K high-DPI frames (Playwright lives in repo-root node_modules)
NODE_PATH="$PWD/node_modules" node launch/onboarding_video/record_realapp_4k.mjs

# 3. assemble 4K
bash launch/onboarding_video/assemble_realapp_4k.sh
# verify: ffprobe must report 3840×2160, ~64s, h264
```

## 1080p pipeline (original, soft — kept for reference)

```bash
# servers as above, then:
# 2. record (Playwright lives in repo-root node_modules)
NODE_PATH="$PWD/node_modules" node launch/onboarding_video/record_realapp.mjs

# 3. assemble
bash launch/onboarding_video/assemble_realapp.sh
```

## Verification frames (gitignored)

- `4k_frame_{1..3}_*.png` — extracted from the FINAL **4K** mp4 at set-password,
  messages/mutual, and threads. Each is 3840×2160 with visibly sharp UI text and
  shows ONLY demo personas (Alex Rivera / Thomas Weber / Sofia Reyes / Priya Nair).
- `realapp_frame_{1..5}_*.png` — same idea from the older 1080p cut.

## Audio — music only (VO is a follow-up)

No voiceover (ElevenLabs out of scope). `assemble_realapp.sh` muxes
`../our_version/music.mp3` only. TODO in that script shows the two-input amix to
restore VO once `voiceover.mp3` exists.

## Demo data left in place (clean up when done with the video)

- Attendee **Alex Rivera** `alex.video@demo.proofoftalk.io` (id printed by the
  staging script) — DELEGATE, privacy=full, real embedding.
- 4 matches Alex ↔ {Thomas Weber, Priya Nair, Amara Okafor, Sofia Reyes};
  **Thomas Weber is set mutual** (`status/status_a/status_b = accepted`).
- A demo-only thread `rwa_tokenisation_demo` ("Tokenisation & RWA — Builders
  Circle") with 3 demo-persona posts. (An earlier run also left 3 demo posts in
  the public `tokenisation_of_finance` thread — harmless demo content.)
- After the recording, Alex has a real `users` row (the on-camera claim) +
  whatever message/post/booking the run created, and his matches were rebuilt to
  the demo set. To fully reset: delete the Alex attendee + its user/matches/
  messages/posts rows (all keyed off `alex.video@demo.proofoftalk.io`).

All of the above is `@demo.proofoftalk.io` and excluded from every metric.
