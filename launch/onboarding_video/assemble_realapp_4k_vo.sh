#!/usr/bin/env bash
# assemble_realapp_4k_vo.sh — VOICEOVER cut of the 4K real-app onboarding video.
#
# Same crisp 3840×2160 frame sequence as assemble_realapp_4k.sh, but:
#   - NO burned-in drawtext captions (the ElevenLabs VO carries the narration)
#   - audio = Brian VO at full level (1.0) + music as a quiet bed UNDERNEATH,
#     sidechain-ducked by the VO (music dips when Brian speaks, lifts in the gaps)
#
# Inputs:
#   frames4k/frame_NNNNNN.jpg        3840×2160 frames (record_realapp_4k.mjs)
#   frames4k/beats.json              per-frame on-camera offsets (real-time concat)
#   4k_vo_track.mp3                  beat-synced VO track (generate_vo_4k.sh)
#   ../our_version/music.mp3         music bed
# Output:
#   pot_onboarding_realapp_4k_vo.mp4   (leaves the captioned 4K + 1080p in place)
#
# Run:  bash launch/onboarding_video/generate_vo_4k.sh   # once, to make the VO
#       bash launch/onboarding_video/assemble_realapp_4k_vo.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMES_DIR="$DIR/frames4k"
BEATS="$FRAMES_DIR/beats.json"
CONCAT="$FRAMES_DIR/concat_vo.txt"
MUSIC="$DIR/../our_version/music.mp3"
VO="$DIR/4k_vo_track.mp3"
OUT="$DIR/pot_onboarding_realapp_4k_vo.mp4"
FPS=30

[ -f "$BEATS" ] || { echo "no beats.json in $FRAMES_DIR — run record_realapp_4k.mjs first" >&2; exit 1; }
[ -f "$VO" ]    || { echo "no VO track at $VO — run generate_vo_4k.sh first" >&2; exit 1; }
ls "$FRAMES_DIR"/frame_000001.jpg >/dev/null 2>&1 || { echo "no frames in $FRAMES_DIR — run record_realapp_4k.mjs first" >&2; exit 1; }

# Build the real-time concat list (each frame held for its wall-clock delta).
python3 - "$BEATS" "$FRAMES_DIR" "$CONCAT" <<'PY'
import json, sys, os
beats_path, frames_dir, concat_path = sys.argv[1:4]
d = json.load(open(beats_path))
times = d["frame_times"]
ext = d.get("ext", "jpg")
n = len(times)
lines = []
for i in range(n):
    fpath = os.path.join(frames_dir, f"frame_{i+1:06d}.{ext}")
    if not os.path.exists(fpath):
        continue
    dur = max(0.001, round(times[i+1] - times[i], 4)) if i < n - 1 else 0.10
    lines.append(f"file '{fpath}'")
    lines.append(f"duration {dur}")
if lines:
    last_file = next(l for l in reversed(lines) if l.startswith("file "))
    lines.append(last_file)
open(concat_path, "w").write("\n".join(lines) + "\n")
print(f"[assemble4k-vo] concat list: {n} frames, on-camera duration {d['duration_s']}s")
PY

DUR=$(python3 -c "import json;print(round(json.load(open('$BEATS'))['duration_s'],3))")
echo "[assemble4k-vo] target ~${DUR}s @ ${FPS}fps   vo: $VO   music: $MUSIC"

# Video filter: re-time to constant 30fps, yuv420p. NO captions.
VF="fps=${FPS},format=yuv420p"

# Audio mix:
#   [1] = music, [2] = VO.
#   - music: gentle bed level + fade in/out, then sidechain-compressed (ducked)
#     keyed off the VO so it dips while Brian speaks and lifts in the gaps.
#   - VO: full level (slight bump for presence).
#   - amix VO + ducked music; VO drives loudness.
FADE_OUT_START=$(python3 -c "print(round($DUR-2.5, 3))")
FILTER_A="\
[1:a]volume=0.55,afade=t=in:st=0:d=1.5,afade=t=out:st=${FADE_OUT_START}:d=2.5[mus];\
[2:a]volume=1.0,asplit=2[vo_mix][vo_key];\
[mus][vo_key]sidechaincompress=threshold=0.05:ratio=12:attack=20:release=400:makeup=1[ducked];\
[vo_mix][ducked]amix=inputs=2:normalize=0:dropout_transition=0[a]"

ffmpeg -y -loglevel error -stats \
  -f concat -safe 0 -i "$CONCAT" \
  -i "$MUSIC" \
  -i "$VO" \
  -filter_complex "[0:v]${VF}[v];${FILTER_A}" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -t "$DUR" \
  -movflags +faststart \
  "$OUT"

echo "[assemble4k-vo] wrote $OUT"
ffprobe -v error \
  -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate \
  -show_entries format=duration \
  -of default=noprint_wrappers=1 "$OUT"
