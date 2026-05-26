#!/usr/bin/env bash
# build_unified_60s.sh
# Builds a unified ≤60s 4K Karl walkthrough by concatenating segments from
# two source films with xfade crossfades. Outputs a SILENT video first;
# the VO + ducked music mix is layered on by the companion script.
#
# Sources (read-only):
#   A: matchmaker_content/raw/marcus-walkthrough-4k-true-voiceover.mp4 (landing-page hero, Marcus walkthrough)
#   B: launch/onboarding_video/pot_onboarding_realapp_4k_vo.mp4 (real-app onboarding)
#
# Storyboard segment plan lives in matchmaker_content/storyboard/storyboard.json
set -euo pipefail
cd "$(dirname "$0")/.."

A="matchmaker_content/raw/marcus-walkthrough-4k-true-voiceover.mp4"
B="launch/onboarding_video/pot_onboarding_realapp_4k_vo.mp4"
OUT_DIR="matchmaker_content/edited"
SILENT="$OUT_DIR/_unified_silent_4k.mp4"
mkdir -p "$OUT_DIR"

# Segments: src_label in_s out_s
# Source B real timeline:
#   34-40s = Thomas Weber message screen (typing → sent)
#   42-44s = transition/loading
#   44-46s = Matias Hagen match card (#1)
#   46-50s = Thomas Weber MUTUAL MATCH + free-slot booking panel  ← KEY
#   54-58s = Discussion Threads landing
#   58-64s = Tokenisation & RWA thread with posts
SEGS=(
  "A 0.0 7.0"    # 1 hero
  "B 0.4 7.4"    # 2 set password
  "B 9.0 16.0"   # 3 profile regenerate
  "A 8.5 15.0"   # 4 matches why it matters (Marcus's matches w/ Daniel Kim)
  "B 35.0 40.5" # 5 messages → typing → sent (Thomas — would love to walk you through)
  "B 45.5 49.5"  # 6 MUTUAL MATCH + free slots (Thomas Weber)
  "B 58.5 63.5"  # 7 threads (Tokenisation & RWA thread)
  "A 1.0 7.5"    # 8 cta close
)
XFADE=0.4

# Build the ffmpeg filtergraph.
INPUTS=()
FILTER=""
N=${#SEGS[@]}

# Two-pass approach for reliability:
#  pass 1: render each segment to its own normalised mp4 (3840x2160@30 yuv420p)
#  pass 2: feed all 8 normalised mp4s into a single ffmpeg with chained xfade
SEG_DIR="$OUT_DIR/_segs"
mkdir -p "$SEG_DIR"
rm -f "$SEG_DIR"/seg_*.mp4

declare -a SEG_FILES
declare -a DURS
for i in "${!SEGS[@]}"; do
  read -r lbl s e <<< "${SEGS[$i]}"
  case "$lbl" in
    A) src="$A" ;;
    B) src="$B" ;;
  esac
  dur=$(awk -v a="$s" -v b="$e" 'BEGIN{printf "%.3f", b-a}')
  DURS+=("$dur")
  out="$SEG_DIR/seg_$(printf '%02d' "$i").mp4"
  SEG_FILES+=("$out")
  echo "[seg $i] $lbl $s -> $e  (dur=${dur}s)  -> $out"
  ffmpeg -y -hide_banner -loglevel error \
    -ss "$s" -to "$e" -i "$src" \
    -vf "scale=3840:2160:flags=lanczos,fps=30,format=yuv420p,setsar=1" \
    -an \
    -c:v libx264 -pix_fmt yuv420p -crf 18 -preset medium \
    -r 30 \
    "$out"
done

# Pass 2: pairwise xfade by repeatedly composing two clips at a time.
# Chained xfade in a single filtergraph silently truncates the final input;
# doing it pairwise as intermediate files is reliable.
probe_dur() {
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"
}

RUNNING="$SEG_DIR/run_00.mp4"
cp "${SEG_FILES[0]}" "$RUNNING"
RUNNING_DUR="$(probe_dur "$RUNNING")"

for ((i=1; i<N; i++)); do
  off=$(awk -v c="$RUNNING_DUR" -v x="$XFADE" 'BEGIN{printf "%.3f", c-x}')
  next="$SEG_DIR/run_$(printf '%02d' "$i").mp4"
  echo "[xfade $i] running_dur=${RUNNING_DUR}s offset=${off}s + seg dur=${DURS[$i]}s"
  ffmpeg -y -hide_banner -loglevel error \
    -i "$RUNNING" -i "${SEG_FILES[$i]}" \
    -filter_complex "[0:v][1:v]xfade=transition=fade:duration=$XFADE:offset=$off,format=yuv420p[v]" \
    -map "[v]" -an \
    -c:v libx264 -pix_fmt yuv420p -crf 18 -preset medium \
    -r 30 \
    "$next"
  RUNNING="$next"
  RUNNING_DUR="$(probe_dur "$RUNNING")"
  echo "[xfade $i] new running_dur=${RUNNING_DUR}s"
done

cp "$RUNNING" "$SILENT"
echo "[build] expected final duration ≈ ${RUNNING_DUR}s"

echo "[build] wrote $SILENT"
ffprobe -v error -show_entries stream=codec_name,width,height,duration -show_entries format=duration "$SILENT"
