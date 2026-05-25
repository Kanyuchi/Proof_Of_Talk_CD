# PROOF OF TALK MATCHMAKER — GETTING STARTED

Onboarding Video Script — On-Screen Text & Animation Reference

~82 seconds · 13 scenes · 4 acts · 4K 60fps

**Purpose:** Walk a brand-new attendee end-to-end — from buying/redeeming a ticket OR
receiving the welcome email with the magic link, through setting up, to booking meetings.
The spine of the film is the **mutual-match consent model**, told deliberately so the
"I accepted but can't see them in Messages / can't message them" confusion never happens.
This is the companion to the launch film (`POT Matchmaker — Video Script.md`) and reuses
its visual system.

---

## How to read this document

Each section = one scene, in playback order.

ON-SCREEN TEXT — every word that appears on screen, in order.

ANIMATIONS — timing and motion for each element. Times are seconds from the start of that
scene (local, not global).

### Persistent Watermark (all scenes except 01 and 13)

POT logo — white, 28px, top-left (60px from left, 50px from top). Inverted to black on
light scenes. Fades in over 1s at start, out over 1s at end.

---

## ━━ ACT 1 — YOU'RE IN ━━

### Scene 01 · Title

**Time:** 0:00 – 0:04 (4.0s)

**Background:** Pure white

**ON-SCREEN TEXT**

> **YOU'RE IN.** *Large heading, black*
>
> **[Proof of Talk logo]** *POT wordmark, inverted to black*
>
> **Matchmaker** *Giant italic orange — 200px Poppins*
>
> **From ticket to your first meeting — in minutes.** *Subtitle — small grey*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| YOU'RE IN | 0.05s | 0.5s | easeOutCubic | Fade + slide up 8px, word by word |
| POT Logo | 0.5s | 0.5s | easeOutCubic | Fade + slide up 12px |
| Matchmaker | 0.85s | per word 0.07s | easeOutCubic | Word-by-word reveal, slide up 20px |
| Subtitle | 1.6s | per word 0.022s | easeOutCubic | Word-by-word reveal |

---

### Scene 02 · Two ways in

**Time:** 0:04 – 0:09 (5.0s)

**Background:** Pitch black

**ON-SCREEN TEXT**

> **Two ways into the room.** *Centered headline — 80px italic Poppins, white*
>
> **1 · You bought or redeemed a ticket** *Left card — white, mono label "TICKET"*
>
> **2 · You got the welcome email** *Right card — orange accent, mono label "MAGIC LINK"*
>
> **Either way — same destination: your matches.** *Subtitle, grey, beneath both cards*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Headline | 0.2s | 0.6s | easeOutCubic | Fade + slide up 16px |
| Left card | 0.8s | 0.5s | easeOutBack | Scale pop 0.85→1.0 |
| Right card | 1.0s | 0.5s | easeOutBack | Scale pop 0.85→1.0 |
| Converging lines | 1.6s | 0.6s | easeInOutCubic | Two lines draw down from cards to a single point |
| Subtitle | 2.2s | 0.5s | easeOutCubic | Fade + slide up 10px |

---

### Scene 03 · Path 1 — Ticket → account

**Time:** 0:09 – 0:15 (6.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Bought a ticket?** *LEFT PANEL — italic, 86px, white*
>
> **Create your account with the email you bought it with.** *LEFT PANEL — subtitle, grey*
>
> **meet.proofoftalk.io** *RIGHT PANEL — browser bar, mono*
>
> **Register** *Form card heading*
>
> **Email — you@company.com** *Field 1 — with helper "the email on your ticket"*
>
> **Password — ••••••••** *Field 2*
>
> **[ Create account → ]** *Orange CTA*
>
> **✓ Ticket found — you're verified** *Green confirmation chip*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Register card | 0.6s | 0.5s | easeOutCubic | Fade + slide up 16px |
| Email field | 1.1s | 0.4s | easeOutCubic | Field fills, typewriter |
| Password field | 1.7s | 0.4s | easeOutCubic | Field fills with dots |
| Cursor taps CTA | 2.4s | 0.25s | easeInOutCubic | Cursor scale-down + ripple |
| Green verified chip | 2.9s | 0.5s | easeOutBack | Scale pop + glow |

**NOTE (not on screen):** reinforces the real rule — register with the *ticket* email so the
gate finds you. If someone buys mid-day, their ticket syncs shortly; the welcome-email path
(Scene 04) is the instant alternative.

---

### Scene 04 · Path 2 — Welcome email → magic link

**Time:** 0:15 – 0:21 (6.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Got the email?** *LEFT PANEL — italic, 86px, white*
>
> **One tap. No password. Straight to your matches.** *LEFT PANEL — subtitle, grey*
>
> **[POT Logo]** *Email card header*
>
> **From hello@proofoftalk.io** *Sender, mono grey*
>
> **Your introductions are ready.** *Email subject — 44px*
>
> **[ Open my matches → ]** *Single orange CTA*
>
> *— cursor taps, email slides out, app drops in —*
>
> **Welcome to Proof of Talk** *Landing heading — real app copy*
>
> **Set a password to save your spot (optional)** *Small grey line under heading*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Email card | 0.2s | 0.5s | easeOutCubic | Fade + slide up 16px |
| CTA button | 0.7s | 0.4s | easeOutBack | Scale pop + glow |
| Cursor taps CTA | 1.3s | 0.25s | easeInOutCubic | Cursor scale-down + ripple |
| Email exit | 1.4s | 0.4s | easeInCubic | Slide up + fade out |
| Landing heading | 1.8s | 0.5s | easeOutCubic | Fade + slide up 16px |
| Password line | 2.4s | 0.4s | easeOutCubic | Fade in |

---

## ━━ ACT 2 — SET UP IN 30 SECONDS ━━

### Scene 05 · Make your matches sharper

**Time:** 0:21 – 0:27 (6.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Tell it what you want.** *LEFT PANEL — italic, 86px*
>
> **A few lines now = far better matches.** *LEFT PANEL — subtitle, grey*
>
> **Your goals at POT 2026** *RIGHT PANEL — field label*
>
> **Raising a seed round · seeking infra VCs and custody partners** *Field text, typewriter*
>
> **Your write-up** *Second field label*
>
> **This is how you're introduced to your matches — edit it anytime.** *Helper line, grey*
>
> **[ Regenerate with AI ]** *Small pill, orange outline*
>
> **✓ Saved. Matches refreshing.** *Green confirmation banner*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Goals field | 0.7s | 0.5s | easeOutCubic | Field fills, typewriter |
| Write-up field | 1.8s | 0.5s | easeOutCubic | Field fills, typewriter |
| Regenerate pill | 2.6s | 0.4s | easeOutBack | Scale pop |
| Green banner | 3.2s | 0.5s | easeOutCubic | Fade + slide up 10px |

**NOTE:** showcases the new self-service write-up edit + regenerate (shipped 2026-05-25).

---

## ━━ ACT 3 — HOW MATCHING WORKS (THE IMPORTANT BIT) ━━

### Scene 06 · Your matches, ranked

**Time:** 0:27 – 0:32 (5.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Your matches.** *LEFT PANEL — italic, 86px*
>
> **Ranked. With a reason for every one.** *LEFT PANEL — subtitle*
>
> **#1 Complementary · Good match** *Card header*
>
> **[Photo] Mira Chen / GP · Vega Ventures** *Name + role*
>
> **COMPATIBILITY: 82%** *Score, green*
>
> **Why this meeting matters — She raises from the LPs you need.** *Orange insight box*
>
> **[ Accept ]   [ Decline ]** *Two action buttons under the card*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Match card | 0.9s | 0.6s | easeOutCubic | Slide in from right 40px |
| Shimmer | 1.6s | 0.65s | easeInOutCubic | White shine sweeps |
| Action buttons | 2.2s | 0.45s | easeOutBack | Pills scale-pop in together |

---

### Scene 07 · Accepting sends a request

**Time:** 0:32 – 0:38 (6.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Accepting is step one.** *LEFT PANEL — italic, 80px*
>
> **It sends them a request — it doesn't open a chat yet.** *LEFT PANEL — subtitle, grey*
>
> *— cursor taps [ Accept ] on Mira's card —*
>
> **You accepted Mira** *Status pill on card*
>
> **Awaiting their acceptance** *Amber badge — REAL app copy*
>
> **They've been notified. You'll know the moment they say yes.** *Reassurance line, grey*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Cursor taps Accept | 0.8s | 0.25s | easeInOutCubic | Cursor scale-down + pill ripple |
| Card flips to "accepted" | 1.1s | 0.45s | easeOutCubic | Button row morphs to status pill |
| Amber "awaiting" badge | 1.6s | 0.45s | easeOutBack | Scale pop |
| Reassurance line | 2.2s | 0.5s | easeOutCubic | Fade + slide up 10px |

**NOTE:** this scene exists specifically to set the expectation. "Awaiting their acceptance"
is the real string from the app (Messages thread header).

---

### Scene 08 · Chat unlocks when BOTH say yes (the key scene)

**Time:** 0:38 – 0:45 (7.0s)

**Background:** Pitch black

**ON-SCREEN TEXT**

> **Chat opens when you both accept.** *Centered headline — 84px italic Poppins, 'both' in orange*
>
> *— a simple two-step diagram animates left → right —*
>
> **You ✓** *Left node — your avatar, green check*
>
> **Mira …** *Middle node — Mira's avatar, pulsing "pending"*
>
> *— then Mira's node flips to a green check, an orange line connects them —*
>
> **Mira ✓** *Middle node resolves to green check*
>
> **Mutual match — both accepted!** *Green banner — REAL app copy*
>
> **Now it's in your Messages. Now you can write.** *Sub-line, grey*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Headline | 0.2s | 0.6s | easeOutCubic | Fade + slide up 16px |
| 'You ✓' node | 1.0s | 0.5s | easeOutBack | Scale pop, green check draws |
| 'Mira …' node (pending) | 1.3s | 0.5s | easeOutBack | Scale pop, dots pulse |
| Mira flips to ✓ | 2.6s | 0.5s | easeOutBack | Pending dots → green check |
| Orange connector | 3.0s | 0.5s | easeInOutCubic | ScaleX grows left→right |
| Green mutual banner | 3.6s | 0.55s | easeOutCubic | Fade + slide up 12px |
| Sub-line | 4.3s | 0.5s | easeOutCubic | Fade + slide up 10px |

**NOTE:** the heart of the film — directly answers "why can't I see my accepted match in
Messages / why can't I message them." Mirrors the real empty-state copy: *"Chat opens when
both attendees accept the same match."*

---

### Scene 09 · Now you can message

**Time:** 0:45 – 0:51 (6.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Messages.** *LEFT PANEL — italic, 86px*
>
> **Unlocked. Write whatever you like.** *LEFT PANEL — subtitle*
>
> **Mira Chen — Mutual match** *RIGHT PANEL — thread header, green dot*
>
> **YOU** *Chat label, mono*
>
> **Hi Mira — loved your last fund's thesis. Free to talk LPs on Day 1?** *Custom message bubble, right aligned, typewriter*
>
> **[ Type a message… ]** *Active input field — enabled, not greyed*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Thread header | 0.7s | 0.45s | easeOutCubic | Fade + slide up 12px |
| Input field enables | 1.1s | 0.4s | easeOutCubic | Greyed → solid, subtle glow |
| Custom message bubble | 1.6s | 0.6s | easeOutCubic | Fade + slide up 14px, typewriter |

**NOTE:** explicitly shows the composer ENABLED and a free-text custom message — the second
half of the user's feedback ("it doesn't allow me to send a custom message").

---

### Scene 10 · Lock in the meeting

**Time:** 0:51 – 0:56 (5.0s)

**Background:** Pitch black (split layout)

**ON-SCREEN TEXT**

> **Then book it.** *LEFT PANEL — italic, 86px*
>
> **Shared free slots. One tap.** *LEFT PANEL — subtitle*
>
> **Both free at — tap to book** *RIGHT PANEL — card header, REAL app copy*
>
> **Wed 11:30** *Slot pill — HIGHLIGHTED orange*
>
> **● CONFIRMED — Wed · 11:30** *Confirmation card*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Left panel | 0s | 1.4s | useFeatureTransition | Opacity crossfade |
| Slot pills (5, staggered) | 0.9s | per pill 0.1s | easeOutBack | Scale pop |
| Cursor taps Wed 11:30 | 1.7s | 0.25s | easeInOutCubic | Cursor + orange highlight |
| Confirmed card | 2.2s | 0.55s | easeOutCubic | Fade + slide up 16px |

---

## ━━ ACT 4 — KEEP COMING BACK ━━

### Scene 11 · Why it's worth checking back

**Time:** 0:56 – 1:03 (7.0s)

**Background:** Pitch black

**ON-SCREEN TEXT**

> **It keeps working while you don't.** *Headline — 80px italic, white*
>
> **New matches as people join** *Stat row 1 — orange tick*
>
> **Connection requests waiting for your yes** *Stat row 2 — orange tick*
>
> **Replies from your mutual matches** *Stat row 3 — orange tick*
>
> **Check back. Your room keeps growing.** *Closing sub-line, grey*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Headline | 0.2s | 0.6s | easeOutCubic | Fade + slide up 16px |
| Stat row 1 | 1.0s | 0.45s | easeOutCubic | Fade + slide up 10px |
| Stat row 2 | 1.4s | 0.45s | easeOutCubic | Fade + slide up 10px |
| Stat row 3 | 1.8s | 0.45s | easeOutCubic | Fade + slide up 10px |
| Sub-line | 2.5s | 0.5s | easeOutCubic | Fade + slide up 10px |

**NOTE:** "Connection requests" is the real MyMatches tab where one-sided accepts from
others wait — turning the consent model into a reason to return rather than a dead end.

---

### Scene 12 · One line to remember

**Time:** 1:03 – 1:08 (5.0s)

**Background:** Cream / light

**ON-SCREEN TEXT**

> **Accept the people you want.** *Line 1 — 52px Fraunces serif, dark*
>
> **When they accept back, the conversation opens.** *Line 2 — 52px Fraunces serif, orange italic*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| Line 1 | 0.2s | 0.55s | easeOutBack | Spring pop — translateY 30px→0 + fade |
| Line 2 | 1.2s | 0.55s | easeOutBack | Spring pop — translateY 30px→0 + fade |

---

### Scene 13 · CTA

**Time:** 1:08 – 1:13 (5.0s)

**Background:** Pitch black

**ON-SCREEN TEXT**

> **[Proof of Talk logo]** *POT wordmark — white, 200px*
>
> **LOUVRE PALACE · PARIS · JUNE 2–3, 2026** *Date line — mono caps, grey*
>
> **Open your matches. They're already in the room.** *Tagline — 28px, grey*
>
> **[ meet.proofoftalk.io → ]** *Orange pill button*

**ANIMATIONS**

| Element | Delay | Duration | Easing | Animation |
|---|---|---|---|---|
| POT Logo | 0s | 0.7s | easeOutCubic | Fade + slide up 22px |
| Date line | 0.6s | 0.55s | easeOutCubic | Fade + slide up 12px |
| Tagline | 0.85s | 0.55s | easeOutCubic | Fade + slide up 12px |
| CTA button | 1.35s | 0.55s | easeOutBack | Scale pop + glow |

---

## Appendix — Global Constants (shared with the launch film)

**Canvas:** 1920 × 1080 (renders 4K via 2× scale) · **FPS:** 60 · **Duration:** ~82s

**Fonts:** Poppins (display) · Inter (body) · JetBrains Mono (mono) · Fraunces (serif chapter)

**Orange:** #F76A0C · **Dark bg:** rgb(8,8,8) + 0.9% crosshatch · **Light bg:** rgb(250,248,245)
· **Green (match):** rgb(34,197,94) · **Amber (pending):** rgb(245,158,11)

**Easing:** easeOutCubic (reveals) · easeInOutCubic (transitions) · easeOutBack (spring pops)
· easeInCubic (exits) · useFeatureTransition (split-layout left fade / right vertical slide)

---

## Appendix — Source-of-truth for on-screen strings

On-screen copy is matched to the real app / real flows so the film teaches the actual product:

- **Register requires the ticket email** (gate) — [backend/app/api/routes/auth.py:66-75](../backend/app/api/routes/auth.py#L66-L75)
- **Magic-link welcome email + landing** — [backend/app/services/email.py](../backend/app/services/email.py), [frontend/src/pages/MagicMatches.tsx:94](../frontend/src/pages/MagicMatches.tsx#L94)
- **Editable write-up + "Regenerate with AI"** (Scene 05) — [frontend/src/pages/Profile.tsx](../frontend/src/pages/Profile.tsx)
- **Match card: type, "Why this meeting matters", Compatibility** — [frontend/src/pages/MyMatches.tsx](../frontend/src/pages/MyMatches.tsx)
- **One-sided accept → status_a/status_b; overall stays pending** — [backend/app/api/routes/matches.py:575-610](../backend/app/api/routes/matches.py#L575-L610)
- **"Awaiting their acceptance"** badge (Scene 07) — [frontend/src/pages/Messages.tsx:188-192](../frontend/src/pages/Messages.tsx#L188-L192)
- **"Chat opens when both attendees accept the same match"** (Scene 08) — [frontend/src/pages/Messages.tsx:89](../frontend/src/pages/Messages.tsx#L89)
- **"Mutual match — both accepted!"** banner — [frontend/src/pages/MyMatches.tsx:649-651](../frontend/src/pages/MyMatches.tsx#L649-L651)
- **Composer enabled only on mutual** (Scene 09 inverse) — [frontend/src/pages/Messages.tsx:235-239](../frontend/src/pages/Messages.tsx#L235-L239)
- **Messages list shows mutual (or already-messaged) matches** — [backend/app/api/routes/messages.py:96-99](../backend/app/api/routes/messages.py#L96-L99)
- **"Both free at — tap to book"** chip — [frontend/src/pages/MyMatches.tsx:690-691](../frontend/src/pages/MyMatches.tsx#L690-L691)
- **"Connection Requests" tab** (Scene 11) — [frontend/src/pages/MyMatches.tsx:66-73](../frontend/src/pages/MyMatches.tsx#L66-L73)

Advertising placeholders (not literal app data): attendee names (Mira Chen / Vega Ventures),
venue/room names, illustrative meeting copy.
