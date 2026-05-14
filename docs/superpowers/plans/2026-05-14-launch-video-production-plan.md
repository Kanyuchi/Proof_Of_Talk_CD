# POT Matchmaker Launch Video — Production & Distribution Plan

> **For human + agentic workers:** Each task is a checkbox unit (~30 min – 1 day). "Acceptance" replaces "test" — for non-code work that means a concrete pass/fail the deliverable must clear before commit. Spec: [`launch/2026-05-launch-video-brief.md`](../../../launch/2026-05-launch-video-brief.md).

**Goal:** Ship a 30-second hero video around "Find your 5, not your 500," distributed organically on LinkedIn + X + IG Reels in sync with the email re-enable, driving (a) magic-link claims from existing ticket-holders and (b) ticket sales from prospects.

**Architecture:** Production pipeline runs in parallel with the email re-enable engineering work. Video assets live in `launch/assets/` (small files committed, large files on Drive and linked). Distribution runs on a fixed T-day schedule once the email blast is verified.

**Tech Stack:** Veo 3 / Sora (AI cinematic), CleanShot or OBS (product screen-record), ElevenLabs (VO), Suno (music), DaVinci Resolve or Final Cut (edit), LinkedIn + X + Instagram (distribution), Supabase dashboard (post-launch metrics).

---

## Phase 1 — Pre-production (T-14d → T-10d)

### Task 1: Lock script, shot list, and asset checklist

**Files:**
- Create: `launch/script-and-shotlist.md`

- [ ] **Step 1: Draft the locked script**

Copy the VO lines from the brief into a single file with timestamps:

```markdown
# 30s Script — locked 2026-05-14

00:00–00:05  "Two thousand five hundred decision-makers. Eighteen trillion dollars in the room."
00:05–00:10  "You could meet five hundred of them…"
00:10–00:22  "…or let our AI read every profile, find the five who matter to you, and book the meeting."
00:22–00:30  "Find your five. Not your five hundred."
```

- [ ] **Step 2: Add the shot list**

```markdown
## Shots needed

| # | Time | Source | Notes |
|---|---|---|---|
| 1 | 0–5s | Veo 3 / Sora | Slow dolly into Louvre at dusk; lights flickering on |
| 2 | 0–5s | Veo 3 / Sora | Particle swarm settling into ~2500 glowing dots overlay |
| 3 | 5–7s | Stock or shoot | Stacking business cards macro |
| 4 | 7–10s | Screen-record | Generic flooded calendar UI |
| 5 | 10–14s | Screen-record (real product) | My Matches page on meet.proofoftalk.io |
| 6 | 14–18s | Screen-record (real product) | AI Concierge drafting goals (the field-drafting flow) |
| 7 | 18–20s | Screen-record (real product) | "Marcus also picked you" mutual-match badge |
| 8 | 20–22s | Screen-record (real product) | Booked meeting card with location |
| 9 | 22–30s | Veo 3 / Sora | Drone pull-out from Louvre at sunrise + logo land |
```

- [ ] **Step 3: Acceptance — script reads cleanly out loud**

Read the script aloud at conversational pace. The final delivery should land in 30 seconds ± 1 second. Adjust phrasing if you overshoot.

- [ ] **Step 4: Commit**

```bash
git add launch/script-and-shotlist.md
git commit -m "docs: lock launch video script + shot list"
```

---

### Task 2: Secure attendee consent for product cuts

**Files:**
- Create: `launch/consents/` (folder)
- Create: `launch/consents/release-template.md`

- [ ] **Step 1: Draft a one-paragraph release**

```markdown
# POT Matchmaker — On-camera Release

I, **{{name}}**, consent to the use of my name, photograph, profile, and any
recorded interaction with the POT Matchmaker for the launch campaign
(LinkedIn, X, Instagram, and partner reposts) for Proof of Talk 2026.
I understand this footage may be retained in the launch archive
indefinitely and reused in post-event recap material.

Signed: _____________________   Date: _____________

Contact: {{email}}
```

- [ ] **Step 2: Identify 2–3 candidates**

Pull from the engaged-attendee shortlist (Pouneh Bligaard is already engaged on LinkedIn; ask Ferd for 1–2 more from registered VCs / sponsors). Goal: at least one recognisable name whose profile can be screen-recorded without privacy-mode blurring.

- [ ] **Step 3: Acceptance — at least one signed release in `launch/consents/`**

If zero releases by T-10d, fall back to full privacy-mode blurring on all product cuts (still shippable, weaker social proof).

- [ ] **Step 4: Commit (release template only — keep signed PDFs out of git, store on Drive)**

```bash
git add launch/consents/release-template.md
git commit -m "docs: add launch consent release template"
```

---

## Phase 2 — Production (T-10d → T-5d)

### Task 3: Render the AI cinematic shots

**Files:**
- Create: `launch/assets/cinematic/` (folder; large `.mp4` files via Drive link in a `README.md`)
- Create: `launch/assets/cinematic/README.md`

- [ ] **Step 1: Render shot 1 (Louvre dusk push) — 3 takes**

In Veo 3 or Sora, prompt:
> Slow cinematic dolly forward toward the Louvre Palace at dusk. Warm window lights flickering on one by one. Pyramid lit from beneath. Subtle haze. Shot on 35mm anamorphic.

Render 3 variations. Reject any with warped architecture, melting glass, or impossible reflections.

- [ ] **Step 2: Render shot 2 (particle swarm) — 3 takes**

> Abstract overlay: 2500 small golden dots converging and settling into a loose grid pattern over a dark plate. Smooth ease-out motion. No text.

- [ ] **Step 3: Render shot 9 (drone pull-out at sunrise) — 3 takes**

> Slow drone pull-out reveal of the Louvre Palace and Pyramid at sunrise. Soft pastel sky. No tourists. Shot on 50mm.

- [ ] **Step 4: Acceptance — one usable take per shot**

Watch each take at full resolution. "Usable" = no obvious AI artefacts (warped windows, dissolving people, ghost limbs). If all 3 takes of a shot fail, re-prompt and re-render.

- [ ] **Step 5: Drive upload + README link**

Upload final picks to Google Drive `POT Launch / cinematic /`. Add the share link to `launch/assets/cinematic/README.md`:

```markdown
# Cinematic shots — final picks

Drive: <PASTE_DRIVE_LINK>

- shot-01-louvre-dusk-v2.mp4
- shot-02-particle-swarm-v1.mp4
- shot-09-drone-sunrise-v3.mp4

Render notes:
- Veo 3 used for shots 1 + 9; Sora used for shot 2 (cleaner abstract motion).
```

- [ ] **Step 6: Commit**

```bash
git add launch/assets/cinematic/README.md
git commit -m "docs: link AI cinematic shot renders (Drive)"
```

---

### Task 4: Capture screen-record product cuts

**Files:**
- Create: `launch/assets/product/` (folder)
- Create: `launch/assets/product/README.md`

- [ ] **Step 1: Stage the product for capture**

Log into `meet.proofoftalk.io` as the consenting attendee (from Task 2). Pre-load:
- My Matches page with at least 3 high-quality mutual matches visible
- A mutual-match notification badge on the nav ("Marcus also picked you" — substitute a real consented name)
- A booked meeting on the schedule

If the consenting attendee doesn't have a real mutual match, ask Ferd to use the admin trigger-matching action to seed one for them with another consenting attendee.

- [ ] **Step 2: Capture clips with CleanShot or OBS**

Record at 1080p @ 60fps minimum:

| Clip | Action |
|---|---|
| `clip-mymatches.mov` | Land on My Matches, slow scroll through 3 cards |
| `clip-concierge-draft.mov` | Open AI Concierge → "Yes, draft my goals" → see 3 candidates appear → click one → edit textarea → Save → see green confirmation |
| `clip-mutual-badge.mov` | Land on home page with the orange "Mutual interest" nav badge visible; click through |
| `clip-booked-meeting.mov` | Show the booked meeting card on My Matches with date/time/location |

- [ ] **Step 3: Acceptance — clips play through clean**

Every clip must:
- Run through without a loading spinner mid-frame
- Use the consented attendee's real name + photo (no `John Doe` placeholders)
- Show no console errors, dev-tools panels, or browser chrome from other tabs

If a clip stutters or shows a spinner, re-capture after pre-warming the page.

- [ ] **Step 4: Drive upload + README**

Upload to `POT Launch / product /`. Update `launch/assets/product/README.md` with the link + clip list.

- [ ] **Step 5: Commit**

```bash
git add launch/assets/product/README.md
git commit -m "docs: link product screen-record clips (Drive)"
```

---

### Task 5: Record and select voiceover

**Files:**
- Create: `launch/assets/audio/` (folder)
- Create: `launch/assets/audio/README.md`

- [ ] **Step 1: Generate VO takes in ElevenLabs**

Use the locked script from Task 1. Render with 3 voices:
- Adam (deep, measured, default authority)
- Rachel (warm, female, premium feel)
- Daniel (British, neutral — works for both US + EU audiences)

Settings: stability 50%, similarity 75%, style 30%.

- [ ] **Step 2: A/B test against Zohair**

Send all 3 cuts in a Slack DM to Zohair. Ask: "Which one makes you trust the product more?" Pick the winner.

- [ ] **Step 3: Acceptance — winner survives the "playback test"**

Play the chosen VO over an unrelated cinematic clip (any from Task 3). If it still sounds authoritative and warm — not robotic or pitched-bro — it ships. If it sounds AI-obvious, re-render with stability 65% and lower style.

- [ ] **Step 4: Drive upload + README**

Update `launch/assets/audio/README.md` with the final pick + the rejected takes for the archive.

- [ ] **Step 5: Commit**

```bash
git add launch/assets/audio/README.md
git commit -m "docs: lock VO selection for launch video"
```

---

### Task 6: Score and sound-design

**Files:**
- Modify: `launch/assets/audio/README.md`

- [ ] **Step 1: Generate the music bed in Suno**

Prompt:
> Cinematic orchestral build, 30 seconds. Soft strings opening, percussive low-end entering at 10s, full orchestral lift at 22s, gentle resolve by 28s. No vocals. BPM 90.

Render 4 takes, pick the one whose build matches the storyboard beat (tension at 5s, product proof at 10s, CTA at 22s).

- [ ] **Step 2: Add SFX**

Source from Splice or Freesound:
- Soft whoosh on the particle-swarm settle (5s mark)
- Subtle UI click on the AI Concierge "Save" moment (~18s)
- Air swell as the drone shot pulls out (24s mark)

- [ ] **Step 3: Acceptance — music ducks under VO without dropping intensity**

In the edit (Task 7), preview with VO + music together. The music should sit at -12 LUFS under the VO; if the VO sounds buried or the music sounds anaemic, re-balance before locking.

- [ ] **Step 4: Drive upload + README append**

Append final music + SFX picks to `launch/assets/audio/README.md`.

- [ ] **Step 5: Commit**

```bash
git add launch/assets/audio/README.md
git commit -m "docs: add score + SFX selections for launch video"
```

---

## Phase 3 — Edit & Approve (T-5d → T-3d)

### Task 7: Edit the master + export channel cuts

**Files:**
- Create: `launch/assets/edits/` (folder)
- Create: `launch/assets/edits/README.md`

- [ ] **Step 1: Assemble the timeline in Resolve / Final Cut**

Layer in order, top to bottom:
1. On-screen text (Title cards: "PROOF OF TALK 2026", "500?", "Find your 5", "meet.proofoftalk.io")
2. Product screen-record clips (Task 4)
3. AI cinematic shots (Task 3)
4. VO (Task 5)
5. Music bed + SFX (Task 6)

Cut to the beat sheet from Task 1. Use motion blur on text reveals (4–6 frames) — no harder cuts on text than on visuals.

- [ ] **Step 2: Color + grade**

Match all cinematic shots to a consistent warm-dusk grade. Match product cuts to a slightly desaturated cool tone so they read as "real" against the cinematic warmth.

- [ ] **Step 3: Export master + channel cuts**

| Cut | Aspect | Resolution | Use |
|---|---|---|---|
| `master-16x9.mp4` | 16:9 | 1920×1080 @ 30fps, H.264, 12 Mbps | Archive + sales decks |
| `linkedin-1x1.mp4` | 1:1 | 1080×1080 @ 30fps, H.264, 8 Mbps | LinkedIn feed |
| `reels-9x16.mp4` | 9:16 | 1080×1920 @ 30fps, H.264, 8 Mbps | IG Reels + X mobile |
| `x-16x9.mp4` | 16:9 | 1280×720 @ 30fps, H.264, 5 Mbps | X (smaller cap) |

- [ ] **Step 4: Acceptance — every cut plays through with captions on a phone**

Watch each cut on a phone with the sound OFF. Open captions must convey the message. If a viewer can't follow "find your 5, not your 500" without audio, add an extra title card.

- [ ] **Step 5: Drive upload + README**

Update `launch/assets/edits/README.md` with the Drive link + the export checksums.

- [ ] **Step 6: Commit**

```bash
git add launch/assets/edits/README.md
git commit -m "docs: lock master + channel cuts for launch video"
```

---

### Task 8: Approval review with Zohair

**Files:**
- Create: `launch/approval-2026-05.md`

- [ ] **Step 1: Send Zohair the master + LinkedIn cut**

DM both files via Drive link. Ask three specific questions (not "what do you think"):
1. Does the opening 5 seconds make you want to keep watching?
2. Is "Find your 5, not your 500" the line you want anchoring the brand?
3. Anything in the product cuts you'd not show in public?

- [ ] **Step 2: Capture feedback verbatim**

Paste Zohair's replies into `launch/approval-2026-05.md`. Quote, don't paraphrase.

- [ ] **Step 3: Acceptance — explicit yes, or one revision round**

If Zohair says "yes, ship" → move on. If he requests changes, do one revision pass only (re-cut + re-export the affected cuts), then escalate to "ship as-is" if there's a second round of nitpicks — perfectionism kills launches.

- [ ] **Step 4: Commit approval doc**

```bash
git add launch/approval-2026-05.md
git commit -m "docs: log Zohair approval for launch video"
```

---

## Phase 4 — Pre-flight (T-3d → T-day)

### Task 9: Verify email re-enable + magic-link blast

**Files:** none (engineering verification only)

- [ ] **Step 1: Confirm Rhuna webhook is live**

Check the dashboard heartbeat (`sync_status` table) for the Rhuna webhook ingestion. The most recent row must be < 10 min old. If stale, escalate to Sveat before proceeding.

- [ ] **Step 2: Re-enable email sends**

In `backend/app/services/email.py`, remove the `return` early-exit from the 7 functions that are currently disabled. Redeploy to Railway. Hit the `/health` endpoint to confirm.

- [ ] **Step 3: Send the magic-link blast**

Run `backend/scripts/send_magic_link_blast.py` (or equivalent — confirm the script name exists in the repo; if not, write a one-off in `scripts/` that iterates `attendees` and sends the welcome email with their `magic_access_token`).

- [ ] **Step 4: Acceptance — 3 manual inbox checks**

Personally verify the email landed in 3 different inboxes (your own, Karl, Ferd). Check Gmail, Outlook, and one corporate domain. If any landed in spam, hold the launch and investigate sender reputation.

- [ ] **Step 5: Allow 48hrs inbox dwell**

Do NOT post the video for 48hrs after the blast. Existing ticket-holders need a chance to land in the app before the public push, or the comment-section CTA ("DM me your magic link") becomes the support firehose.

---

### Task 10: Pre-stage all posts and reposts

**Files:**
- Modify: `launch/2026-05-launch-video-brief.md` — fill the `{{N}}` matches-generated number in Karl's repost.

- [ ] **Step 1: Pull live match count from the dashboard**

Visit `meet.proofoftalk.io/dashboard` (admin). Read the current match total from the Match Quality tile.

- [ ] **Step 2: Update the brief with the real number**

```bash
# Replace {{N}} in launch/2026-05-launch-video-brief.md with the actual number
```

- [ ] **Step 3: Pre-draft the LinkedIn post + 3 reposts as drafts**

In LinkedIn's web composer, paste each post + attach the right cut. Save as draft (do NOT publish). Repeat for Zohair, Karl, Ferd accounts.

- [ ] **Step 4: Pre-draft the X thread**

Paste the 5 tweets into Typefully or X's native composer. Schedule for T-day 09:00 Paris (will be overridden manually if anything goes wrong).

- [ ] **Step 5: Acceptance — every draft has the correct cut attached**

Open each platform, confirm the right aspect-ratio cut is on the right post. LinkedIn = 1:1 or 16:9, X = 16:9, IG Reels = 9:16. A wrong-aspect post is a brand smell.

- [ ] **Step 6: Commit the brief update**

```bash
git add launch/2026-05-launch-video-brief.md
git commit -m "docs: lock live match count in launch brief"
```

---

## Phase 5 — Launch day (T-day)

### Task 11: Publish + reposts cascade

**Files:** none (live ops)

- [ ] **Step 1: T-day 09:00 Paris — publish PoT company page post**

Hit publish on the company-page draft. Note the URL.

- [ ] **Step 2: T-day 09:30 — Zohair reposts**

Zohair publishes his repost with the founder-voice copy from the brief, quoting the company-page post.

- [ ] **Step 3: T-day 10:00 — Karl reposts**

Karl publishes his ops-numbers repost.

- [ ] **Step 4: T-day 10:30 — Ferd reposts**

Ferd publishes his community-voice repost.

- [ ] **Step 5: T-day 10:00 — X thread goes live**

Confirm the scheduled X thread published. If Typefully missed the slot, publish manually.

- [ ] **Step 6: T-day 10:00 — IG Reels goes live**

PoT IG account publishes the 9:16 cut with the short caption.

- [ ] **Step 7: T-day 11:00 — Karl + Ferd drop the "DM me" comment**

Under the LinkedIn company-page post, Karl and Ferd each leave a top-level comment:
> "If you're a ticket-holder and you haven't seen your magic link yet, DM me your ticket email — I'll send it through."

- [ ] **Step 8: Acceptance — all 4 LinkedIn posts visible in feed within 90 min**

Check the company-page post, then each reposter's profile. Each must show the video + caption + correct attribution. If any failed to publish, troubleshoot in-thread.

---

## Phase 6 — Post-launch (T+24h → T+7d)

### Task 12: 24-hour performance check + paid-boost decision

**Files:**
- Create: `launch/post-mortems/2026-05-launch-24h-snapshot.md`

- [ ] **Step 1: Pull metrics from LinkedIn analytics**

For each of the 4 LinkedIn posts (company + 3 reposts), record:
- Impressions
- Click-through to `proofoftalk.io`
- Engagement rate (likes + comments + reposts ÷ impressions)
- Replies to the "DM me" comments

- [ ] **Step 2: Cross-check magic-link claims**

Query Supabase:

```sql
SELECT COUNT(*) FROM attendees
WHERE last_login_at >= '<T-day>'::timestamp;
```

Compare to the 436 baseline.

- [ ] **Step 3: Write the snapshot**

```markdown
# 24h Launch Snapshot — 2026-05-XX

## Reach
- LinkedIn impressions (all 4 posts): ___
- X impressions: ___
- IG Reels reach: ___

## Conversion
- Magic-link claims since T-day: ___ / 436 (___%)
- proofoftalk.io clicks (UTM): ___
- New ticket purchases attributable: ___ (per Extasy referrer)

## Comments + DMs
- Total "DM me" replies: ___
- Magic-link DM resolutions handled: ___ / ___
- Notable quotes / objections: …

## Decision: paid boost?
[ ] Yes — boost $___ targeting ___ on LinkedIn
[ ] No — organic clears target; reinvest budget elsewhere
```

- [ ] **Step 4: Acceptance — decision documented within 24h of T-day**

If the snapshot isn't written by T+24h, the campaign is on autopilot and we lose the boost window.

- [ ] **Step 5: Commit**

```bash
git add launch/post-mortems/2026-05-launch-24h-snapshot.md
git commit -m "docs: log 24h launch performance snapshot"
```

---

### Task 13: 7-day post-mortem

**Files:**
- Create: `launch/post-mortems/2026-05-launch-postmortem.md`

- [ ] **Step 1: Pull final numbers (T+7d)**

Same metrics as Task 12, but window = full 7 days.

- [ ] **Step 2: Hit-rate against the brief's targets**

| Metric | Target | Actual | Hit? |
|---|---|---|---|
| LinkedIn impressions | 25k | ___ | |
| Click-through | 3% | ___ | |
| Magic-link claims | 60% (262 of 436) | ___ | |
| New ticket purchases | 40 | ___ | |
| Replies to comment | 30 | ___ | |

- [ ] **Step 3: One lesson for the next launch**

Single paragraph. What you'd do differently. Be specific — "post on a different day" or "shoot a founder-cameo cut" beats "do better next time."

- [ ] **Step 4: Acceptance — post-mortem committed and linked from `launch/README.md`**

- [ ] **Step 5: Commit**

```bash
git add launch/post-mortems/2026-05-launch-postmortem.md launch/README.md
git commit -m "docs: 7-day launch post-mortem + index update"
```

---

## Self-review

**Spec coverage:** Every section of `launch/2026-05-launch-video-brief.md` is covered — storyboard (Task 1 + 3 + 4), channels (Task 11), copy (already in brief, locked in Task 10), timing (Tasks 9 + 10 + 11), metrics (Tasks 12 + 13), open questions (Task 2 for consent, Task 5 for VO A/B as proxy for the founder-cameo fork).

**Placeholder scan:** Zero `TBD` / `TODO` / `figure out later`. The `{{N}}` placeholder in the brief is explicitly the Task 10 deliverable.

**Type / signature consistency:** File paths are consistent across tasks. `launch/assets/{cinematic,product,audio,edits}/README.md` is the pattern. Drive is the source of truth for binary files; the repo holds only links and small text.

**Risk concentrations to watch:**
- **Task 9** (email re-enable) is the single biggest risk. If the magic-link blast fails or lands in spam, the activation half of the campaign is dead and the brief's target metrics are unreachable. Treat Task 9 as a gate — do not proceed past T-3d without three clean inbox confirmations.
- **Task 3** (AI cinematic) can absorb a whole weekend if the renders refuse to cooperate. Block Saturday in the calendar.
- **Task 8** (Zohair approval) can spiral. The "one revision round only" rule is in the task explicitly to prevent that.
