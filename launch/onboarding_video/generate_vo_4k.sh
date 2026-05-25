#!/usr/bin/env bash
# generate_vo_4k.sh — generate a beat-synced ElevenLabs MALE voiceover track for
# the 4K real-app onboarding video, then stitch the per-line clips onto a single
# ~64s VO track timed to the recording's REAL beat offsets (frames4k/beats.json).
#
# Why per-line clips + adelay/amix (mirrors the launch film's stitched VO):
#   Each narration line is generated as its own mp3, then placed at its beat's
#   start offset via ffmpeg `adelay` (delay = beat offset in ms) and merged with
#   `amix`. That keeps each line locked to the moment its UI step is on screen,
#   with natural silence in the gaps — instead of one wall-to-wall take that
#   drifts off the visuals.
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

[ -f "$ENV_FILE" ] || { echo "no backend/.env at $ENV_FILE" >&2; exit 1; }
[ -f "$BEATS" ]    || { echo "no beats.json — run record_realapp_4k.mjs first" >&2; exit 1; }

# Pull the key WITHOUT printing it.
API_KEY="$(grep -E '^ELEVENLABS_API_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r\n')"
[ -n "$API_KEY" ] || { echo "ELEVENLABS_API_KEY not set in backend/.env" >&2; exit 1; }

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
for i in "${!LABELS[@]}"; do
  label="${LABELS[$i]}"
  text="${TEXTS[$i]}"
  out="$VO_DIR/${label}.mp3"
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

# ── Resolve per-line start offsets from beats.json (seconds) ──────────────────
# CTA is anchored a fixed offset before the end so the threads-reply visual reads
# first, then the call to action lands in the final ~4s.
read_offsets() {
  python3 - "$BEATS" "$VO_DIR" <<'PY'
import json, sys, os, subprocess
beats_path, vo_dir = sys.argv[1:3]
d = json.load(open(beats_path))
bt = {b["label"]: b["t"] for b in d["beats"]}
end = d["duration_s"]

def dur(p):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())

# (label, slot) pairs must match the bash arrays above.
plan = [
    ("line1","beat1"), ("line2","beat2"), ("line3","beat3"),
    ("line4","beat4"), ("line5","beat5"), ("line6","beat6"), ("cta","cta"),
]
# Small lead-in so the visual reads ~0.4s before the VO starts on each beat.
LEAD = 0.4
rows = []
for label, slot in plan:
    mp3 = os.path.join(vo_dir, f"{label}.mp3")
    dlen = dur(mp3)
    if slot == "cta":
        # land the CTA so it ENDS ~0.6s before the video end
        start = max(0.0, end - 0.6 - dlen)
    else:
        start = bt[slot] + LEAD
    rows.append((label, round(start,3), round(dlen,3)))
# guard: clamp so a line never overruns the next line's start (trim handled in mix)
for (label, start, dlen) in rows:
    print(f"{label} {start} {dlen}")
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
