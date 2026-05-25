# Onboarding Video — Shot List, Asset Checklist & Production Plan

**What:** 60-second "Getting Started" explainer. Script: `POT Matchmaker — Onboarding Video Script.md`.
VO: `POT Matchmaker — Onboarding Voiceover.md`.

**Why (origin):** an attendee reported "I accepted matches but can't see them in Messages / can't
send a custom message." That's the designed mutual-consent behaviour, but the confusion deters
first use & return. This film makes the whole flow obvious so the mutual-match step reads as
intentional — and shows Threads as the way to talk *without* waiting for a match.

**Format:** primarily **real-app screen recordings** (not AI cinematic) — it's a product
walkthrough. AI/B-roll only for the opening hook if desired. Mirrors the launch video pipeline
(screen-record → ElevenLabs VO → music → DaVinci/FCP edit → captions).

**Distribution (differs from the launch film — this is onboarding/retention, not acquisition):**
embed in the **welcome email**, the **magic-link landing** (`/m/:token`), an in-app **"How it
works"** link, and **reuse in support replies** (e.g. the messaging-confusion thread). Optional
short cut for social.

---

## Asset checklist

- [ ] **Demo account** with rich, realistic data — use a demo persona (`marcus@demo.proofoftalk.io`
      / `ProofDemo2026!`) so no real attendee data is shown. Pre-load: a complete profile, 5+
      ranked matches, one match that can be driven to mutual, an active Threads tab.
- [ ] **Second demo account** ("Mira") to perform the reciprocal Accept for the mutual-match beat
      (Scene 06) — record both sides, or stage the accept via a second browser/device.
- [ ] **Clean browser** — 1920×1080, no extensions/bookmarks bar, cursor highlighting on.
- [ ] **Screen recorder** — CleanShot/OBS, 60fps, capture at 4K or 2× retina.
- [ ] **Welcome email** rendered in a clean inbox view (or a faithful mock) for Scene 02.
- [ ] **VO** — ElevenLabs, from `POT Matchmaker — Onboarding Voiceover.md` (10 lines).
- [ ] **Music** — Suno or licensed bed; soft, optimistic, ducks under VO.
- [ ] **Brand kit** — POT logo (white + black), orange #F76A0C, fonts (Poppins/Inter/JetBrains/Fraunces).
- [ ] **Captions** — burned-in (most onboarding views are muted-autoplay).

---

## Screen-recording shot list (mapped to script scenes)

Record each cleanly; the editor trims to the scene window. "Route" = where in the app to capture.

| Scene | Window | Capture | Route / action | Notes |
|---|---|---|---|---|
| 01 | 0:00–0:05 | Title card (motion graphics, not screen) | — | Built in edit: "YOU'RE IN" + Matchmaker + hook line. AI/Louvre B-roll optional behind. |
| 02 | 0:05–0:12 | **Welcome email → magic link** | Inbox view of the welcome email; cursor taps **"Open my matches"** | Show sender `hello@proofoftalk.io`, subject "Your introductions are ready." End on the tap. |
| 03 | 0:12–0:18 | **Set a password (claim)** | `/m/:token?unlock=1` landing → type password → Save | The "make it yours" step. End on success/redirect into matches. |
| 04 | 0:18–0:25 | **Enrich profile** | `/profile` → type Goals → edit **Your write-up** → click **Regenerate with AI** → Save | Show the green "matches refreshing" confirmation. Highlights the new editable write-up. |
| 05 | 0:25–0:30 | **Matches, ranked** | `/matches` → top card with type, 82%, "Why this meeting matters" | Hover so the Accept/Decline buttons are visible. |
| 06 | 0:30–0:39 | **Accept → mutual → unlock** | Tap **Accept** → show **"Awaiting their acceptance"** → (cut to Mira accepting) → **"Mutual match — both accepted!"** | THE key beat. Capture the amber pending state AND the green mutual banner. May need both accounts. |
| 07 | 0:39–0:45 | **Message + book** | `/messages` mutual thread → type a custom message (show composer ENABLED) → tap a "Both free at" slot → Confirmed | Prove the composer works post-mutual + one-tap booking. |
| 08 | 0:45–0:52 | **Threads** | `/threads` → scroll topic threads → open one → type a reply | Show it's open to anyone, no match required — the pre-match conversation route. |
| 09 | 0:52–0:56 | Pay-off card (motion graphics) | — | "Accept who you want / When they accept back, the conversation opens." |
| 10 | 0:56–1:00 | CTA card (motion graphics) | — | POT logo + date line + "Open your matches" + meet.proofoftalk.io. |

**Recording tips:** move the cursor deliberately and slowly; pause ~1s on each key UI element so
the editor has handles; record each scene 2–3× for safe takes; keep the same demo data across all
captures so names/cards stay consistent.

---

## Assembly notes

- Cut to the **script scene timings** (the script's timing table sums to 60.0s).
- Drop **VO** on the `start_s` marks from the voiceover track; duck music under VO.
- **Burn captions** from the VO lines (verbatim) for muted autoplay.
- Use the launch film's visual system for the 3 motion-graphics cards (01, 09, 10): orange #F76A0C,
  Fraunces serif for pay-off lines, same logo treatment — so the two films feel like a set.
- Keep on-screen UI strings real (they already match the app per the script's source-of-truth appendix).

---

## Acceptance (pass/fail before "done")

- [ ] Runs **≤ 60s**, all 10 beats present and legible at mobile size.
- [ ] Scene 06 clearly shows **pending → mutual → messages unlocked** (the core teaching moment).
- [ ] Scene 08 clearly shows **Threads as a no-match-needed conversation route**.
- [ ] No real attendee data on screen (demo personas only).
- [ ] Captions match VO; VO matches the script.
- [ ] Approved by Shaun + Zohair before distribution.

---

## Next actions (the "start")

1. [ ] Stage the two demo accounts + data (profile, matches, a driveable-to-mutual match, threads).
2. [ ] Record scenes 02–08 (screen capture) per the shot list.
3. [ ] Generate VO (ElevenLabs) from the voiceover track.
4. [ ] Build the 3 motion-graphics cards (01, 09, 10) + assemble in DaVinci/FCP.
5. [ ] Review pass against Acceptance → ship to welcome email + magic-link landing + in-app "How it works".
