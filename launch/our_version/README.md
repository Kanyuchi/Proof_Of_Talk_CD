# our_version — language + structure pass on Sithum's video

A working copy of Sithum's React/Babel browser-rendered launch video, edited so the on-screen copy and one rebuilt scene mirror the real app UI per [POT Matchmaker — Video Script.md](../POT%20Matchmaker%20—%20Video%20Script.md).

**Sithum's original is preserved at `launch/from_sithum/`** — diff against it to see exactly what changed.

## What changed (video2.jsx only)

| Sithum component | Our script scene | Change |
|---|---|---|
| `Scene07` | Scene 07 — My Matches | Subtitle → "Your top introductions, ranked." Three cards now span all real match types (Complementary / Non-Obvious / Deal Ready), each with the app's exact descriptor. "DEAL READY %" score label → "COMPATIBILITY %". "Why this matters" → "Why this meeting matters". |
| `Scene08` | Scene 09 — Concierge Chat | Added static input placeholder "Ask about attendees, meetings, connections…" (real app copy from `ChatPanel.tsx:180`). |
| `SceneIntro09` | Scene 10 — chapter card | "Auto Profile" → "Drafted for you". Subtitle → "Concierge drafts. You approve. Matches refresh." |
| `Scene09` | Scene 11 — Profile | **Full rebuild.** Replaced form-fill UX with the actual `ProfilePromptOffer` chat flow: Concierge welcome → "[ Yes, draft my goals ]" / "[ Maybe later ]" pills → three candidate chips → tap → "✓ Saved. Matches refreshing." |
| `Scene10` | Scene 13 — Mutual Match | Banner "✓ Mutual match — you both said yes" → "Mutual match — both accepted!" (real app copy from `MyMatches.tsx:649`). |
| `Scene11` | Scene 15 — One-tap Booking | Header "Free slots you both have" → "Both free at — tap to book". Subtext "Calendar invite sent to both of you." → "Locked in. They'll see it in their matches too." (calendar-invite sending isn't built). |
| `Scene12` | Scene 17 — Magic Link | **Full rebuild.** Email card → cursor tap → magic-link landing. Email subject "Your introductions are ready, Mira." (real subject from `email.py:167`). Landing heading "Welcome, Mira" (real copy from `MagicMatches.tsx:94`) + 3 mini match cards. Dropped the 3-row meeting list. |
| `Scene13` | Scene 18 — Impact close | 3 serif lines → 2-line home-page hero: "Tell us what you need. / We'll tell you who to meet." (real copy from `Home.tsx:19-24`). |
| `Scene14Availability` | Scene 19 — Built Into POT | Typo "Build Into" → "Built Into". |

## How to run locally

This directory's `index.html` references binary assets (audio, photos, logos) that live in `../from_sithum/`. They are intentionally not committed (~22MB). To play the video:

```bash
# From the repo root, copy the binaries from Sithum's snapshot
cp launch/from_sithum/*.mp3 launch/from_sithum/*.png launch/our_version/
cp -R launch/from_sithum/figures launch/our_version/

# Serve and open in browser
cd launch/our_version && python3 -m http.server 8765
# → http://localhost:8765/?render=1
```

The `?render=1` URL param disables autoplay and exposes `window.__seek(t)` for jumping to specific scenes. Example: `window.__seek(43.5)` lands inside the rebuilt Scene 11 (Concierge drafting).

## Smoke-test screenshots

Verified rendering at the key scene timestamps (snapshots in `.playwright-mcp/`):

- `scene07_my_matches.png` (t≈27s) — 3 match types
- `scene09_concierge_drafting.png` (t≈43.5s) — full chat flow
- `scene10_mutual_match.png` (t≈49.5s) — new banner
- `scene11_booking.png` (t≈55.5s) — new header + subtext
- `scene13_close.png` (t≈65s) — home-hero close
- `scene14_built_into.png` (t≈69.5s) — typo fix

## Audio (Brian VO + music)

Voiceover: **Brian — Deep, Resonant, Comforting** (ElevenLabs premade, `nPczCjzI2devNBz1zQrb`). 20 phrases generated separately and stitched with `ffmpeg` silence padding to land each chapter-card callout when its title is fully sharp. See [voiceover_script_v2.md](voiceover_script_v2.md) for per-clip target times.

Music: background track ducks (-12dB) during the VO window (1.0s → 74.5s) and returns to full volume for the final beat.

Robust autoplay: if Chrome blocks audio, any click anywhere on the page resumes both tracks (window-level once-only listener in `app.jsx`). The orange "► Tap to enable sound" pill is the explicit fallback if the user wants to opt-in.

## Mobile viewing

Portrait mobile (≤720px width) shows a "Rotate your phone" splash with an animated icon. The 16:9 video is letterboxed in portrait — landscape gives the full experience. Tested via Chrome DevTools device emulation.

## Download / export to MP4

A Playwright + ffmpeg render script is included. From this directory:

```bash
# One-time setup
npm install --no-save playwright
npx playwright install chromium
brew install ffmpeg                    # or apt/winget equivalent

# Make sure dev server is running
python3 -m http.server 8765 &

# Render at 1080p (default, ~3-5 minutes)
node render.mjs                        # → pot_matchmaker_1080p.mp4

# Render at true 4K (3840×2160, ~10-15 minutes, larger file)
node render.mjs --4k                   # → pot_matchmaker_4k.mp4

# Faster preview render at 30fps
node render.mjs --fps=30
```

The script seeks frame-by-frame via the page's `window.__seek(t)` helper (exposed in `?render=1` mode), screenshots each frame, then ffmpeg muxes the PNG sequence with `voiceover.mp3` + `music.mp3` (mixed at the same -12dB duck levels the live page uses) into an H.264 MP4 with `+faststart` for streaming.

Output file:
- 1080p: ~50–80 MB
- 4K: ~200–400 MB (depending on scene complexity)

The exports are gitignored (`pot_matchmaker_*.mp4`). Upload them to wherever you ship final cuts.
