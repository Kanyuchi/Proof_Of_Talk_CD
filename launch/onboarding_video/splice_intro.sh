#!/usr/bin/env bash
# splice_intro.sh
#
# Builds a combined Karl deliverable =
#   landing-page intro [0 -> CUT_TS] from `marcus-walkthrough-4k-true-voiceover.mp4`
#   + full `pot_onboarding_realapp_4k_vo.mp4`
# with a 0.8s audio crossfade at the splice.
#
# Sources are NOT modified. Output is written to:
#   matchmaker_content/edited/landing-intro-plus-onboarding-4k.mp4
#
# Both inputs are 3840x2160 H.264 + AAC; we re-encode end-to-end via filter_complex
# so the concat boundary is sample-accurate and there are no pix_fmt/timebase joins.

set -euo pipefail

REPO_ROOT="/Users/kanyuchi/Developer/Proof_Of_Talk_CD"
INTRO="${REPO_ROOT}/matchmaker_content/raw/marcus-walkthrough-4k-true-voiceover.mp4"
ONBOARD="${REPO_ROOT}/launch/onboarding_video/pot_onboarding_realapp_4k_vo.mp4"
OUTDIR="${REPO_ROOT}/matchmaker_content/edited"
OUT="${OUTDIR}/landing-intro-plus-onboarding-4k.mp4"

# Cut timestamp: last landing-page frame is ~7.1s, login screen first appears at ~7.2s
# (verified via fps=10 frame inspection — see intro_cut_last_frame.png / intro_cut_after_frame.png).
CUT_TS="7.2"
XFADE="0.8" # audio crossfade duration in seconds

mkdir -p "$OUTDIR"

echo "[splice] intro cut at ${CUT_TS}s, audio xfade ${XFADE}s"
echo "[splice] writing -> $OUT"

# Build the splice in one ffmpeg pass.
#  - [0:v] trimmed to CUT_TS, [1:v] full -> concat
#  - [0:a] trimmed to CUT_TS, [1:a] full -> acrossfade(XFADE)
ffmpeg -y \
  -i "$INTRO" \
  -i "$ONBOARD" \
  -filter_complex "\
    [0:v]trim=start=0:end=${CUT_TS},setpts=PTS-STARTPTS[v0]; \
    [0:a]atrim=start=0:end=${CUT_TS},asetpts=PTS-STARTPTS[a0]; \
    [1:v]setpts=PTS-STARTPTS[v1]; \
    [1:a]asetpts=PTS-STARTPTS[a1]; \
    [v0][v1]concat=n=2:v=1:a=0[vout]; \
    [a0][a1]acrossfade=d=${XFADE}:c1=tri:c2=tri[aout]" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -preset slow -movflags +faststart \
  -c:a aac -b:a 192k \
  "$OUT"

echo "[splice] done"
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height -show_entries format=duration -of default "$OUT"
