# onboarding_video — POT Matchmaker "Getting Started" (60s)

A browser-rendered-React + Playwright/ffmpeg onboarding film that walks a
brand-new attendee through the *flow of use*: buy/redeem ticket → magic-link
welcome email → set a password → enrich profile → matches → the mutual-match
consent gate → message + book → Threads → CTA.

Built on the same system as the launch film in [`../our_version/`](../our_version/).
On-screen text + per-scene timings are implemented exactly per
[`../POT Matchmaker — Onboarding Video Script.md`](../POT%20Matchmaker%20—%20Onboarding%20Video%20Script.md).

## Scenes (10 · 60.0s)

| # | Time | Beat |
|---|---|---|
| 01 | 0:00–0:05 | Title + hook — "YOU'RE IN. / Matchmaker" (white) |
| 02 | 0:05–0:12 | Ticket → redeemed → the welcome email (magic link) |
| 03 | 0:12–0:18 | Tap in → set a password |
| 04 | 0:18–0:25 | Enrich profile (goals + write-up + Regenerate with AI) |
| 05 | 0:25–0:30 | Matches, ranked (#1 Complementary · 82%) |
| 06 | 0:30–0:39 | **Accept → both yes → messages unlock** (the key beat) |
| 07 | 0:39–0:45 | Message + book (Wed 11:30 slot → CONFIRMED) |
| 08 | 0:45–0:52 | Threads — start conversations now (no match needed) |
| 09 | 0:52–0:56 | Pay-off line (cream serif) |
| 10 | 0:56–1:00 | CTA — meet.proofoftalk.io |

Scene 06 is the heart of the film — it deliberately tells the
mutual-consent model ("Chat opens when you **both** accept") so the
"I accepted but can't message yet" confusion never happens.

## Files

- `index.html` — boots React/Babel, exposes `window.__seek(t)` + `window.__renderReady`,
  `?render=1` mode, Stage scene-switching by time. Loads `animations.jsx` then `onboarding.jsx`.
- `onboarding.jsx` — the 10 scenes + mount. Self-contained: it inlines the theme
  constants, the `Scene` crossfade wrapper, `useFeatureTransition`, and the UI-mock
  components (match card, chat/message bubble, slot pills, email card, magic-link
  landing, mutual-match banner, `Portrait`) adapted from `our_version`'s
  `video.jsx`/`video2.jsx` so it does **not** depend on those modules.
- `animations.jsx` — copied verbatim from `our_version` (Stage, Sprite, Easing, etc.).
- `app.jsx` — copied from `our_version` for reference/isolation. **NOT loaded** by
  `index.html` (it targets the launch film's modules + would double-mount React).
- `render.mjs` — Playwright + ffmpeg renderer. `DUR = 60.0`, output `pot_onboarding_1080p.mp4`.
- `smoke.mjs` — boots the page, asserts `__renderReady`, captures the 4 smoke screenshots.

## Run locally

```bash
cd launch/onboarding_video
python3 -m http.server 8765
# → http://localhost:8765/?render=1
```

The `?render=1` param disables autoplay and exposes `window.__seek(t)`.
Example: `window.__seek(34)` lands inside the mutual-match beat (Scene 06).

## Render to MP4

```bash
# One-time setup (playwright is already installed at the repo root)
npm install --no-save playwright
npx playwright install chromium
brew install ffmpeg

# Start the dev server, then render
python3 -m http.server 8765 &
node render.mjs                  # → pot_onboarding_1080p.mp4 (1920×1080 60fps)
node render.mjs --4k             # → pot_onboarding_4k.mp4
node render.mjs --fps=30         # faster preview
```

If `node render.mjs` can't resolve `playwright`, run with the repo-root modules:
`NODE_PATH=../../node_modules node render.mjs`.

Verified: `ffprobe pot_onboarding_1080p.mp4` → `Duration: 00:01:00.00`, 1920×1080, 60 fps.

## Audio — music only (VO is a follow-up)

This cut has **no voiceover yet**. A VO needs ElevenLabs generation, which is out
of scope for this pass, so `render.mjs` muxes **`music.mp3` only** at a gentle
bed level (vol 0.22, 2s fade-in / 3s fade-out).

To add VO later: generate `voiceover.mp3`, then restore the two-input mix in
`render.mjs` (the commented `voArgs` branch shows the exact filter) and add a
`SyncedAudio` component in `onboarding.jsx` mirroring `our_version/app.jsx`.
Both spots are marked with `// TODO: add voiceover.mp3 (ElevenLabs) and restore VO mux`.

## Smoke screenshots

Captured via `window.__seek(t)` (regenerate with `node smoke.mjs` after starting the server):

- `smoke_t02_title.png` (t≈2) — Scene 01 title/hook
- `smoke_t34_mutual.png` (t≈34) — Scene 06 mutual-match beat
- `smoke_t48_threads.png` (t≈48) — Scene 08 Threads
- `smoke_t58_cta.png` (t≈58) — Scene 10 CTA

> Note: the smoke PNGs and all heavy binaries (`*.mp4`, `*.mp3`, `pot-logo.png`,
> `louvre.png`, `figures/`) are gitignored (`*.png` is blocked) — same policy as `our_version`.
> Copy the binaries from `../our_version/` (or `../from_sithum/`) before rendering:
> ```bash
> cp ../our_version/music.mp3 ../our_version/pot-logo.png ../our_version/louvre.png .
> cp -R ../our_version/figures .
> ```
