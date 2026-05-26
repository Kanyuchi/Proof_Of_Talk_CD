# onboarding_video — POT Matchmaker "Getting Started" (REAL APP screen recording)

A ~60s onboarding film that is a **real Playwright screen recording of the
actual POT Matchmaker app** (React on :5173 + FastAPI on :8000, pointed at the
prod Supabase DB), driven through the real onboarding flow by a demo account.

> The earlier JSX-mock cut (`onboarding.jsx` / `app.jsx` / `animations.jsx` /
> `render.mjs` + the `pot_onboarding_1080p.mp4`) was **rejected** — it animated a
> mock UI, not the product. This pipeline records the real UI instead. The mock
> files are left in place for reference but are NOT used to build the deliverable.

## Deliverables

- `pot_onboarding_realapp_4k_vo.mp4` — **TRUE 4K + VOICEOVER** 3840×2160, 30fps,
  ~64s, H.264 (CRF 18) + AAC. **NO on-screen captions** — an ElevenLabs MALE
  voiceover (Brian, beat-synced) carries the narration, with the music bed
  sidechain-ducked underneath. The crisp cut to ship. (See "Voiceover cut" below.)
- `pot_onboarding_realapp_4k.mp4` — **TRUE 4K** 3840×2160, 30fps, ~64s, H.264
  (CRF 18) + AAC music bed. The original captioned cut — built from high-DPI
  screenshot frames (see "4K pipeline" below). Kept in place.
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

- `4k_vo_frame_threads.png` — extracted from the FINAL **VO** mp4 at the threads
  beat (~58s). Confirms NO captions are burned in (only the real app UI is on
  screen) — the VO cut's caption-free check.
- `4k_frame_{1..3}_*.png` — extracted from the FINAL captioned **4K** mp4 at
  set-password, messages/mutual, and threads. Each is 3840×2160 with visibly
  sharp UI text and shows ONLY demo personas (Alex Rivera / Thomas Weber /
  Sofia Reyes / Priya Nair).
- `realapp_frame_{1..5}_*.png` — same idea from the older 1080p cut.

## Voiceover cut (4K, no captions — the one to ship)

A caption-free 4K cut with an ElevenLabs MALE voiceover synced to the recording's
real beat offsets, music ducked under the VO. Reuses the same `frames4k/` frames
+ `beats.json` as the captioned 4K cut — **no re-recording needed**, just
regenerate the VO and re-assemble (fast).

- `generate_vo_4k.sh` — generates the VO. One narration line per beat (+ a closing
  CTA), each line mapped to what is ACTUALLY on screen at its beat and sized to
  fit the beat's duration when spoken (~2.5 w/s). Voice: **Brian — Deep,
  Resonant, Comforting** (ElevenLabs premade `nPczCjzI2devNBz1zQrb`, the same
  male voice as `launch/our_version`), model `eleven_multilingual_v2`, mp3.
  Reads `ELEVENLABS_API_KEY` from `backend/.env` (never printed). Each line is a
  separate mp3 in `frames4k/vo/`, then stitched onto one ~64s track
  (`4k_vo_track.mp3`) by delaying each clip to its beat's start offset (`adelay`)
  and mixing (`amix`) — mirrors how the launch film stitched per-phrase clips.
- `assemble_realapp_4k_vo.sh` — same real-time concat → 3840×2160 H.264, **NO
  drawtext captions**. Audio is now mixed so the **voice clearly dominates**:
  - VO is normalised through `loudnorm=I=-14:TP=-1.5:LRA=11` (broadcast loudness)
    so speech sits front and centre regardless of the source mp3's mastering.
  - Music bed is dropped to `volume=0.06` (≈ -24 dB linear) with a 1.5s fade in
    and 2.5s fade out — already a faint backdrop before any ducking.
  - `sidechaincompress` keyed off the VO (`threshold=0.02:ratio=20:attack=8:release=350`)
    pulls the music down another ~10 dB whenever Brian speaks, then lifts it back
    to the (still quiet) bed in the gaps.
  - Measured on the output: VO segments mean ≈ **-15 dB**, music-only gaps mean
    ≈ **-31 dB** → VO is ~15 dB louder than the bed. The mix is unambiguously
    voice-forward; verify on a re-render with the `volumedetect` snippets below.

```bash
# frames4k/ already exists (from record_realapp_4k.mjs) → just:
bash launch/onboarding_video/generate_vo_4k.sh        # → 4k_vo_track.mp3
#   ↑ idempotent — re-uses frames4k/vo/*.mp3 if present, skips ElevenLabs
#     entirely. Delete the per-line mp3s to force a fresh TTS pass.
bash launch/onboarding_video/assemble_realapp_4k_vo.sh # → pot_onboarding_realapp_4k_vo.mp4
# verify: ffprobe must report 3840×2160, ~64s, h264 + an aac AUDIO stream
```

### Narration lines + beat offsets (FINAL-VIDEO timeline, eyeball-verified)

The original VO pass aligned to `beats.json` capture offsets (when Playwright
DECIDED to navigate). Frame-accurate inspection of the assembled mp4 showed
each scene only renders 2–4s later — e.g. `beat3.t = 21.5s` is the moment
`page.goto('/matches')` fires, but the ranked match cards only paint at
~23.5s. The offsets below come from extracting frames from the assembled
output at candidate offsets and confirming the right visual is on screen.
**If you re-record, re-derive these by extraction** — do not substitute
`beats.json` `t` values.

| # | offset | line | verified on-screen content |
|---|--------|------|----------------------------|
| 1 | 0.4s   | You're in. Tap your magic link, set a password, and your account is ready. | Welcome + "Set your password" + Create my account |
| 2 | 8.0s   | Sharpen your profile. Add your goals, and let the AI draft your write-up — the more it knows, the more of the room it opens. | Profile editor (name/title/Goals/Interests) |
| 3 | 23.5s  | Here are your matches — ranked, scored, and explained, with a reason for every meeting. | "Your Top Introductions…match quality 0.83, Priya Nair Good match" |
| 4 | 34.5s  | Accept the people you want. The moment they accept back, it's a mutual match, and your messages unlock. | Messages with Thomas Weber + composer typing |
| 5 | 46.5s  | Now book a time you're both free — locked in, right there at the Louvre. | "Mutual match — both accepted" + "Both free at — tap to book" chips |
| 6 | 53.0s  | Don't want to wait for a yes? Jump into Threads and start the conversation today. | Discussion Threads list |
| 7 | 61.0s  | Open your matches. They're already in the room. | Builders Circle thread with replies + composer |

### Verify the mix + sync after any rebuild

Audio dominance — VO segments should be at least ~10 dB above music-only gaps:

```bash
# VO segment (line1)
ffmpeg -nostats -ss 1.0 -t 3.0 -i pot_onboarding_realapp_4k_vo.mp4 \
  -af volumedetect -vn -f null - 2>&1 | grep volume
# expect mean ~ -15 dB, max ~ -1 to -2 dB

# Music-only gap (between line2 and line3)
ffmpeg -nostats -ss 15.5 -t 4.5 -i pot_onboarding_realapp_4k_vo.mp4 \
  -af volumedetect -vn -f null - 2>&1 | grep volume
# expect mean ~ -30 dB or lower
```

Sync — extract a frame at each line's start offset and confirm the right
scene is on screen (saved as `sync_check_<beat>.png` in this dir):

```bash
for spec in 0.4:setpassword 8.0:profile 23.5:matches 34.5:mutual \
            46.5:booking 53.0:threads 61.0:cta; do
  off="${spec%%:*}"; lbl="${spec##*:}"
  ffmpeg -y -ss "$off" -i pot_onboarding_realapp_4k_vo.mp4 \
    -frames:v 1 "sync_check_${lbl}.png"
done
```

## Audio — captioned cut uses music only

The captioned cuts (`assemble_realapp.sh`, `assemble_realapp_4k.sh`) mux
`../our_version/music.mp3` only (no VO — the burned-in captions carry the steps).
The VO lives in the caption-free cut above.

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
