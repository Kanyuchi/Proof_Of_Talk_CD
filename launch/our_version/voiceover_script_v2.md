# Voiceover Script v2 — locked to the 76.3s SCHEDULE

Each row is one phrase. `start_s` is the target playhead time when that phrase should begin. ffmpeg will pad silence between phrases to hit these starts exactly.

Voice: Lauren (PVC), settings preserved from the original — stability 50, similarity_boost 75, speed 1.00.

| # | start_s | phrase | scene it lands on |
|---|---|---|---|
| 1 | 0.5 | Introducing Proof of Talk Matchmaker. | Scene 01 INTRODUCING |
| 2 | 4.2 | Two thousand five hundred decision-makers. | Scene 02 (2,500 counter) |
| 3 | 8.2 | Eighteen trillion in combined assets. Ninety-three percent C-suite. | Scene 03 ($18T + 93%) |
| 4 | 13.5 | And somewhere in that room is the conversation that changes your year. | Scene 04 (find the right people) |
| 5 | 18.0 | Matchmaker finds them for you. | SceneHowItWorks bridge |
| 5b | 18.9 | Matchmaker finds them for you. | (shifted +0.9 to avoid overrun) |
| 6 | 21.1 | AI matchmaking. | SceneIntro07 chapter card (shifted +0.7) |
| 7 | 23.3 | Your matches — ranked, scored, explained — before you board the plane. | Scene 07 (My Matches) |
| 8 | 29.5 | AI Concierge. | SceneIntro08 chapter card (shifted +1.5 — clip 7 long) |
| 9 | 31.0 | Ask anything about anyone. Real data, instant prep. | Scene 08 (Concierge Chat) |
| 10 | 36.2 | Drafted for you. | SceneIntro09 chapter card |
| 11 | 39.2 | Concierge writes your profile. One tap to publish. | Scene 09 (rebuilt drafting) |
| 12 | 44.0 | Mutual match. | SceneIntro10 chapter card |
| 13 | 47.0 | When they say yes too — you both know. | Scene 10 (Mutual match) |
| 14 | 50.3 | Smart booking. | SceneIntro11 chapter card |
| 15 | 53.3 | Shared availability. Meeting locked in. | Scene 11 (One-tap booking) |
| 16 | 56.5 | Magic link. | SceneIntro12 chapter card |
| 17 | 59.5 | One link, every meeting, no login. | Scene 12 (Magic Link rebuilt) |
| 18 | 62.4 | The most important meeting of your year is already in that room. | Scene 13 (Impact close) |
| 19 | 67.3 | Built into Proof of Talk. | Scene 14 Availability (Built Into) |
| 20 | 71.5 | Louvre Palace, Paris. June second and third. | Scene 15 CTA (logo + date line) |
| ~~21~~ | — | ~~Claim your ticket.~~ | DROPPED — on-screen orange CTA button is the close; music carries the final beat |

Final stitched runtime: 75.68s (target ≤76.3s). All chapter-card callouts ("AI matchmaking", "AI Concierge", "Drafted for you", "Mutual match", "Smart booking", "Magic link") land on their respective intro cards.

## Generation plan

1. For each phrase, POST to `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}` with model_id `eleven_turbo_v2_5` (or eleven_multilingual_v2 for naturalness).
2. Save each as `vo_NN.mp3` in [voiceover_segments/](voiceover_segments/) (gitignored).
3. Build an ffmpeg `concat` filter with explicit `apad` silence between segments so segment N starts exactly at `start_s[N]`.
4. Output as `voiceover.mp3` (replacing the current desynced one).
5. Verify total duration ≤ 76.3s.
