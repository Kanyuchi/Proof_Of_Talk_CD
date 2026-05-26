#!/usr/bin/env bash
# generate_vo_4k.sh — generate a beat-synced ElevenLabs MALE voiceover track for
# the 4K real-app onboarding video, then stitch the per-line clips onto a single
# ~64s VO track timed to the recording's REAL beat offsets (frames4k/beats.json).
#
# Why per-line clips + adelay/amix (mirrors the launch film's stitched VO):
#   Each narration line is generated as its own mp3, then placed at its
#   start offset via ffmpeg `adelay` (delay in ms) and merged with `amix`. That
#   keeps each line locked to the moment its UI step is on screen, with natural
#   silence in the gaps — instead of one wall-to-wall take that drifts off the
#   visuals.
#
# IMPORTANT — offsets are FINAL-VIDEO timestamps, NOT capture-time beats.
# The first VO pass aligned to `beats.json` capture offsets, which mark when the
# script DECIDED to navigate (e.g. beat3 t=21.48s → page.goto('/matches')).
# Frame-accurate inspection of the assembled mp4 showed each scene only renders
# 2–4s later: the matches grid only paints at ~23s, the messages composer at
# ~34s, the booking chips at ~46s. The hardcoded LINE_STARTS below come from
# extracting frames from the rendered output at candidate offsets and
# eyeballing which moment each line should narrate (set-password panel,
# profile/regenerate write-up, ranked-and-scored match cards, mutual-match
# composer, "Both free at — tap to book" chips, Discussion Threads list, thread
# reply for the CTA). If you re-record, re-derive these by extracting frames
# from the assembled mp4 — capture-time beats are NOT a substitute.
#
# Re-running is idempotent: if line_N.mp3 already exists, the script SKIPS
# ElevenLabs (no API call, no key needed) and just re-stitches. Delete the per-
# line mp3s to force a fresh TTS pass.
#
# Voice: Brian — Deep, Resonant, Comforting (ElevenLabs premade,
#   nPczCjzI2devNBz1zQrb) — same male voice as launch/our_version. Model
#   eleven_multilingual_v2, mp3 output.
#
# Reads ELEVENLABS_API_KEY from backend/.env. The key is never printed.
#
# Output: frames4k/vo/line_N.mp3  (per-line)  +  4k_vo_track.mp3  (stitched, ~64s)
# Then run assemble_realapp_4k_vo.sh to mux this VO over the frames with a ducked
# music bed and NO captions.
#
# Run:  bash launch/onboarding_video/generate_vo_4k.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
ENV_FILE="$REPO/backend/.env"
FRAMES_DIR="$DIR/frames4k"
BEATS="$FRAMES_DIR/beats.json"
VO_DIR="$FRAMES_DIR/vo"
TRACK="$DIR/4k_vo_track.mp3"

VOICE_ID="nPczCjzI2devNBz1zQrb"     # Brian (male) — same as launch/our_version
MODEL="eleven_multilingual_v2"

[ -f "$BEATS" ] || { echo "no beats.json — run record_realapp_4k.mjs first" >&2; exit 1; }
mkdir -p "$VO_DIR"

# ── Narration lines, one per beat (+ a closing CTA in the threads tail) ────────
# Each line is mapped to what is ACTUALLY on screen at its beat and sized to fit
# the beat's duration when spoken by a male VO at ~2.5 w/s.
#   slot = which beat offset to anchor to (from beats.json); the CTA is offset
#   manually near the end of the threads beat.
declare -a LABELS=( line1 line2 line3 line4 line5 line6 cta )
declare -a SLOTS=(  beat1 beat2 beat3 beat4 beat5 beat6 cta )
declare -a TEXTS=(
  "You're in. Tap your magic link, set a password, and your account is ready."
  "Sharpen your profile. Add your goals, and let the AI draft your write-up — the more it knows, the more of the room it opens."
  "Here are your matches — ranked, scored, and explained, with a reason for every meeting."
  "Accept the people you want. The moment they accept back, it's a mutual match, and your messages unlock."
  "Now book a time you're both free — locked in, right there at the Louvre."
  "Don't want to wait for a yes? Jump into Threads and start the conversation today."
  "Open your matches. They're already in the room."
)

# ── Generate each line as its own mp3 via the ElevenLabs REST TTS endpoint ─────
# Skip TTS entirely if every line_*.mp3 + cta.mp3 already exists (re-stitch only).
NEED_TTS=0
for label in "${LABELS[@]}"; do
  [ -s "$VO_DIR/${label}.mp3" ] || { NEED_TTS=1; break; }
done

if [ "$NEED_TTS" -eq 1 ]; then
  [ -f "$ENV_FILE" ] || { echo "no backend/.env at $ENV_FILE (needed for ELEVENLABS_API_KEY)" >&2; exit 1; }
  # Pull the key WITHOUT printing it.
  API_KEY="$(grep -E '^ELEVENLABS_API_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r\n')"
  [ -n "$API_KEY" ] || { echo "ELEVENLABS_API_KEY not set in backend/.env" >&2; exit 1; }

  for i in "${!LABELS[@]}"; do
    label="${LABELS[$i]}"
    text="${TEXTS[$i]}"
    out="$VO_DIR/${label}.mp3"
    if [ -s "$out" ]; then
      echo "[vo] skip ${label} (already exists)"
      continue
    fi
    echo "[vo] generating ${label}: \"${text}\""
    # JSON-escape the text safely via python (handles quotes/em-dashes/apostrophes).
    payload="$(TEXT="$text" MODEL="$MODEL" python3 -c '
import json, os
print(json.dumps({
  "text": os.environ["TEXT"],
  "model_id": os.environ["MODEL"],
  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True},
}))')"
    http_code="$(curl -sS -w '%{http_code}' -o "$out" \
      -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}?output_format=mp3_44100_128" \
      -H "xi-api-key: ${API_KEY}" \
      -H "Content-Type: application/json" \
      -H "Accept: audio/mpeg" \
      -d "$payload")"
    if [ "$http_code" != "200" ]; then
      echo "[vo] ElevenLabs returned HTTP ${http_code} for ${label}:" >&2
      head -c 400 "$out" >&2; echo >&2
      exit 1
    fi
    dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")"
    echo "[vo]   -> ${out} (${dur}s)"
  done
else
  echo "[vo] all per-line mp3s present — skipping ElevenLabs TTS"
fi

# ── Resolve per-line start offsets — FINAL-VIDEO timeline (seconds) ──────────
# These come from extract-and-eyeball verification against the assembled mp4.
# DO NOT replace these with capture-time beats.json offsets — those mark when
# Playwright navigated, NOT when the target scene actually painted (which lags
# 2–4s for the matches grid, messages composer, and booking chips).
#
# Verified target visuals (see sync_check_<label>.png produced by the assembler):
#   line1 @ 0.4s   — set-password panel
#   line2 @ 8.0s   — profile editor (name/title/goals/write-up + Regenerate AI)
#   line3 @ 23.5s  — ranked match cards visible (Priya "Good match" score)
#   line4 @ 34.5s  — mutual thread open w/ composer typing
#   line5 @ 46.5s  — "Mutual match — both accepted" + "Both free at" slot chips
#   line6 @ 53.0s  — Discussion Threads list
#   cta   @ 61.0s  — thread reply being typed in Builders Circle
read_offsets() {
  python3 - "$VO_DIR" <<'PY'
import sys, os, subprocess
vo_dir = sys.argv[1]

LINE_STARTS = [
    ("line1",  0.4),
    ("line2",  8.0),
    ("line3", 23.5),
    ("line4", 34.5),
    ("line5", 46.5),
    ("line6", 53.0),
    ("cta",   61.0),
]

def dur(p):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())

prev_end = -1.0
for label, start in LINE_STARTS:
    mp3 = os.path.join(vo_dir, f"{label}.mp3")
    dlen = dur(mp3)
    if start < prev_end:
        # Should never trigger with the hardcoded offsets above; loud error if so.
        print(f"ERROR: {label} starts at {start} but previous line ended at {prev_end:.3f}", file=sys.stderr)
        sys.exit(2)
    prev_end = start + dlen
    print(f"{label} {start:.3f} {dlen:.3f}")
PY
}

OFFSETS="$(read_offsets)"
echo "[vo] line offsets (label start_s dur_s):"
echo "$OFFSETS"

# ── Stitch: delay each clip to its start offset, mix to a single ~64s track ────
DUR_TOTAL="$(python3 -c "import json;print(json.load(open('$BEATS'))['duration_s'])")"
INPUTS=()
FILTERS=()
MIX_LABELS=""
idx=0
while read -r label start dlen; do
  [ -z "$label" ] && continue
  INPUTS+=( -i "$VO_DIR/${label}.mp3" )
  delay_ms="$(python3 -c "print(int(round($start*1000)))")"
  # adelay all channels, then pad so every stream is full-length for amix.
  FILTERS+=( "[${idx}:a]adelay=${delay_ms}|${delay_ms},apad[a${idx}]" )
  MIX_LABELS="${MIX_LABELS}[a${idx}]"
  idx=$((idx+1))
done <<< "$OFFSETS"

NMIX=$idx
FILTER_COMPLEX="$(IFS=';'; echo "${FILTERS[*]}");${MIX_LABELS}amix=inputs=${NMIX}:normalize=0:dropout_transition=0[vo];[vo]atrim=0:${DUR_TOTAL},asetpts=N/SR/TB[out]"

echo "[vo] mixing ${NMIX} clips into ${TRACK} (len ${DUR_TOTAL}s)"
ffmpeg -y -loglevel error \
  "${INPUTS[@]}" \
  -filter_complex "$FILTER_COMPLEX" \
  -map "[out]" \
  -c:a libmp3lame -q:a 2 \
  "$TRACK"

VO_LEN="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TRACK")"
echo "[vo] wrote $TRACK  (duration ${VO_LEN}s)"
