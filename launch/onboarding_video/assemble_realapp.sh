#!/usr/bin/env bash
# assemble_realapp.sh — turn the raw Playwright screen recording into the final
# 1080p H.264 MP4 with a music bed + burned-in step captions.
#
# Input : launch/onboarding_video/raw/*.webm  (newest; produced by record_realapp.mjs)
# Output: launch/onboarding_video/pot_onboarding_realapp_1080p.mp4
#
# What it does:
#   - speeds the raw up ~1.25x (setpts=PTS/SPEED) so a ~78s capture lands ~63s
#     while staying legible (typing/pauses were deliberately slow in the recorder)
#   - scales 1280x720 -> 1920x1080 (lanczos), 30fps, yuv420p H.264
#   - a 2s "Getting started" intro caption (fade), then per-beat step captions
#     burned into a lower band
#   - music bed (our_version/music.mp3) at vol 0.2 with 1.5s fade-in / 2.5s fade-out
#   - NO voiceover (ElevenLabs out of scope) — TODO below
#
# Run:  bash launch/onboarding_video/assemble_realapp.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="$DIR/raw"
MUSIC="$DIR/../our_version/music.mp3"
FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
OUT="$DIR/pot_onboarding_realapp_1080p.mp4"

SPEED=1.25   # video speed-up factor

# newest webm in raw/
RAW="$(ls -t "$RAW_DIR"/*.webm 2>/dev/null | head -1 || true)"
[ -n "$RAW" ] || { echo "no raw webm in $RAW_DIR — run record_realapp.mjs first" >&2; exit 1; }
echo "[assemble] raw : $RAW"
echo "[assemble] music: $MUSIC"

RAW_DUR="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 "$RAW")"
OUT_DUR="$(echo "$RAW_DUR / $SPEED" | bc -l)"
printf "[assemble] raw=%.1fs  speed=%.2fx  -> out~%.1fs\n" "$RAW_DUR" "$SPEED" "$OUT_DUR"

# Step captions on the FINAL (sped-up) timeline. enable=between(t,a,b).
# Times are approximate beat boundaries in the sped-up output.
TITLE="Getting started"
cap() { # text  start  end
  local t="$1" a="$2" b="$3"
  echo "drawtext=fontfile=${FONT}:text='${t}':fontcolor=white:fontsize=34:box=1:boxcolor=black@0.55:boxborderw=18:x=(w-text_w)/2:y=h-110:enable='between(t\,${a}\,${b})'"
}

# Intro caption (big, centered, fades with the band).
INTRO="drawtext=fontfile=${FONT}:text='${TITLE}':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t\,0\,2.2)'"

# Beat captions (mapped to the ~63s sped-up timeline).
C1="$(cap '1 · Tap your magic link, set a password' 2.4 11)"
C2="$(cap '2 · Sharpen your profile — AI drafts your write-up' 11 26)"
C3="$(cap '3 · Your AI matches, ranked — accept to connect' 26 33)"
C4="$(cap '4 · Mutual match unlocks chat — message them' 33 44)"
C5="$(cap '5 · Both free? Book a slot at the Louvre' 44 52)"
C6="$(cap '6 · Join the pre-event conversations' 52 64)"

VF="setpts=PTS/${SPEED},scale=1920:1080:flags=lanczos,fps=30,format=yuv420p,${INTRO},${C1},${C2},${C3},${C4},${C5},${C6}"

# Music: trim to output length, low volume, fade in/out.
FADE_OUT_START="$(echo "$OUT_DUR - 2.5" | bc -l)"
AF="volume=0.2,afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_OUT_START}:d=2.5"

ffmpeg -y -loglevel error -stats \
  -i "$RAW" \
  -i "$MUSIC" \
  -filter_complex "[0:v]${VF}[v];[1:a]${AF}[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 160k \
  -shortest \
  -movflags +faststart \
  "$OUT"

# TODO: add voiceover. Generate launch/onboarding_video/voiceover.mp3 (ElevenLabs)
# then mix it with the music: replace the [1:a] chain with a two-input amix
# ([1:a]vol 0.18[bed];[2:a]voiceover[vo];[bed][vo]amix=inputs=2:duration=longest).

echo "[assemble] wrote $OUT"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate \
  -show_entries format=duration \
  -of default=noprint_wrappers=1 "$OUT"
