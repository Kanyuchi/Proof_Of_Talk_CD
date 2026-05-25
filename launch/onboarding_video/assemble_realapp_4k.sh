#!/usr/bin/env bash
# assemble_realapp_4k.sh — turn the high-DPI JPEG frame sequence into the final
# TRUE 4K (3840×2160) H.264 MP4 with a music bed + burned-in step captions.
#
# Input : launch/onboarding_video/frames4k/frame_NNNNNN.jpg  (3840×2160 each,
#         produced by record_realapp_4k.mjs) + frames4k/beats.json (per-frame
#         on-camera offsets + caption beat times)
# Output: launch/onboarding_video/pot_onboarding_realapp_4k.mp4
#
# Why this differs from assemble_realapp.sh (the 1080p webm pipeline):
#   - source is a 3840×2160 JPEG sequence (NOT a 1280×720 webm upscaled), so
#     text is genuinely sharp at 4K
#   - 4K screenshots cost ~85ms so the real capture rate is ~10fps. Playing the
#     frames at a naive constant fps would compress the deliberate pauses, so we
#     instead build an ffmpeg CONCAT list with per-frame `duration` taken from
#     beats.json frame_times → playback is TRUE real time (pauses stay pauses,
#     typing stays smooth). The concat is then re-timed to a constant 30fps.
#   - caption font sizes are ~2× the 1080p script (canvas is 4× the area)
#   - caption START/END times are read from beats.json, not hardcoded
#
# Run:  bash launch/onboarding_video/assemble_realapp_4k.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMES_DIR="$DIR/frames4k"
BEATS="$FRAMES_DIR/beats.json"
CONCAT="$FRAMES_DIR/concat.txt"
MUSIC="$DIR/../our_version/music.mp3"
FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
OUT="$DIR/pot_onboarding_realapp_4k.mp4"
FPS=30

[ -f "$BEATS" ] || { echo "no beats.json in $FRAMES_DIR — run record_realapp_4k.mjs first" >&2; exit 1; }
ls "$FRAMES_DIR"/frame_000001.jpg >/dev/null 2>&1 || { echo "no frames in $FRAMES_DIR — run record_realapp_4k.mjs first" >&2; exit 1; }

# Build the concat list: each frame held for the wall-clock delta to the next
# frame (real-time playback). beats.json frame_times[i] is the on-camera offset
# (seconds) of frame i+1. Last frame gets a small tail hold.
python3 - "$BEATS" "$FRAMES_DIR" "$CONCAT" <<'PY'
import json, sys, os
beats_path, frames_dir, concat_path = sys.argv[1:4]
d = json.load(open(beats_path))
times = d["frame_times"]
ext = d.get("ext", "jpg")
n = len(times)
lines = []
for i in range(n):
    fname = f"frame_{i+1:06d}.{ext}"
    fpath = os.path.join(frames_dir, fname)
    if not os.path.exists(fpath):
        continue
    if i < n - 1:
        dur = max(0.001, round(times[i+1] - times[i], 4))
    else:
        dur = 0.10  # tail hold on the last frame
    lines.append(f"file '{fpath}'")
    lines.append(f"duration {dur}")
# concat demuxer needs the last file repeated (no trailing duration) to flush it
if lines:
    last_file = next(l for l in reversed(lines) if l.startswith("file "))
    lines.append(last_file)
open(concat_path, "w").write("\n".join(lines) + "\n")
print(f"[assemble4k] concat list: {n} frames, on-camera duration {d['duration_s']}s")
PY

DUR=$(python3 -c "import json;print(round(json.load(open('$BEATS'))['duration_s'],3))")
echo "[assemble4k] target duration ~${DUR}s @ ${FPS}fps   music: $MUSIC"

# Pull beat caption timestamps from beats.json (seconds).
read_beat_t() { python3 -c "import json; b={x['label']:x['t'] for x in json.load(open('$BEATS'))['beats']}; print(b.get('$1','0'))"; }
B1=$(read_beat_t beat1); B2=$(read_beat_t beat2); B3=$(read_beat_t beat3)
B4=$(read_beat_t beat4); B5=$(read_beat_t beat5); B6=$(read_beat_t beat6)
END="$DUR"
echo "[assemble4k] beat times: b1=$B1 b2=$B2 b3=$B3 b4=$B4 b5=$B5 b6=$B6 end=$END"

# Caption helper — 4K-scaled (fontsize 64; y offset & padding ~2× the 1080p script).
cap() { # text  start  end
  local t="$1" a="$2" b="$3"
  echo "drawtext=fontfile=${FONT}:text='${t}':fontcolor=white:fontsize=64:box=1:boxcolor=black@0.6:boxborderw=34:x=(w-text_w)/2:y=h-210:enable='between(t\,${a}\,${b})'"
}

# Intro caption (big, centered) — fades over the first ~2.2s.
INTRO_END=$(python3 -c "print(round($B1+2.2, 3))")
INTRO="drawtext=fontfile=${FONT}:text='Getting started':fontcolor=white:fontsize=140:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t\,${B1}\,${INTRO_END})'"

# Beat captions span [Bn, B(n+1)).
C1="$(cap '1 · Tap your magic link, set a password'           "$INTRO_END" "$B2")"
C2="$(cap '2 · Sharpen your profile — AI drafts your write-up' "$B2" "$B3")"
C3="$(cap '3 · Your AI matches, ranked — accept to connect'    "$B3" "$B4")"
C4="$(cap '4 · Mutual match unlocks chat — message them'       "$B4" "$B5")"
C5="$(cap '5 · Both free? Book a slot at the Louvre'           "$B5" "$B6")"
C6="$(cap '6 · Join the pre-event conversations'               "$B6" "$END")"

# Re-time concat output to constant 30fps, ensure yuv420p, burn captions.
VF="fps=${FPS},format=yuv420p,${INTRO},${C1},${C2},${C3},${C4},${C5},${C6}"

# Music: low volume, fade in/out, trimmed to video length by -shortest.
FADE_OUT_START=$(python3 -c "print(round($DUR-2.5, 3))")
AF="volume=0.2,afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_OUT_START}:d=2.5"

ffmpeg -y -loglevel error -stats \
  -f concat -safe 0 -i "$CONCAT" \
  -i "$MUSIC" \
  -filter_complex "[0:v]${VF}[v];[1:a]${AF}[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 160k \
  -shortest \
  -movflags +faststart \
  "$OUT"

echo "[assemble4k] wrote $OUT"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,codec_name \
  -show_entries format=duration \
  -of default=noprint_wrappers=1 "$OUT"
