#!/usr/bin/env python3
"""
build_unified_vo.py
Generates 8 ElevenLabs VO clips (one per beat) for the unified Karl walkthrough
video, then mixes them onto a single track timed to the final video offsets,
and finally muxes VO + ducked music onto the silent 4K mp4.

Reads:
  matchmaker_content/storyboard/narration.json
  matchmaker_content/edited/_unified_silent_4k.mp4
  launch/our_version/music.mp3
  backend/.env (ELEVENLABS_API_KEY)

Writes:
  matchmaker_content/edited/_vo/beat_<n>.mp3       per-beat VO
  matchmaker_content/edited/_vo/_vo_track.wav      timed master VO
  matchmaker_content/edited/karl-unified-60s-4k-female-vo.mp4
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
SILENT = ROOT / "matchmaker_content/edited/_unified_silent_4k.mp4"
MUSIC = ROOT / "launch/our_version/music.mp3"
NARR = ROOT / "scripts/unified_video/narration.json"
OUT_DIR = ROOT / "matchmaker_content/edited"
VO_DIR = OUT_DIR / "_vo"
FINAL = OUT_DIR / "karl-unified-60s-4k-female-vo.mp4"

def load_env():
    env = ROOT / "backend/.env"
    for line in env.read_text().splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if k.strip() and v:
            os.environ.setdefault(k.strip(), v)

def probe_dur(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path),
    ])
    return float(out.decode().strip())

def gen_vo(api_key: str, voice_id: str, model_id: str, voice_settings: dict, text: str, out: Path):
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=json.dumps(body).encode(),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs HTTP {e.code}: {e.read().decode()[:300]}")

def main():
    load_env()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("ELEVENLABS_API_KEY missing from backend/.env")

    narr = json.loads(NARR.read_text())
    VO_DIR.mkdir(parents=True, exist_ok=True)

    # Step A: per-beat TTS
    for beat in narr["beats"]:
        out = VO_DIR / f"beat_{beat['n']}.mp3"
        if not out.exists() or out.stat().st_size < 1000:
            print(f"[vo] generating beat {beat['n']} ({len(beat['text'])} chars) -> {out.name}")
            gen_vo(
                api_key=api_key,
                voice_id=narr["voice_id"],
                model_id=narr["model_id"],
                voice_settings=narr["voice_settings"],
                text=beat["text"],
                out=out,
            )
        else:
            print(f"[vo] keeping cached {out.name}")
        print(f"     duration: {probe_dur(out):.2f}s   offset: {beat['offset_s']}s   '{beat['text'][:60]}...'")

    silent_dur = probe_dur(SILENT)
    print(f"[mix] silent video duration: {silent_dur:.3f}s")

    # Step B: build the master VO track via adelay + amix
    vo_inputs = []
    filter_parts = []
    amix_labels = []
    for i, beat in enumerate(narr["beats"]):
        path = VO_DIR / f"beat_{beat['n']}.mp3"
        vo_inputs += ["-i", str(path)]
        delay_ms = int(beat["offset_s"] * 1000)
        # Normalise each clip: ensure mono->stereo, then delay
        filter_parts.append(
            f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={delay_ms}|{delay_ms}[v{i}]"
        )
        amix_labels.append(f"[v{i}]")
    amix = "".join(amix_labels) + f"amix=inputs={len(narr['beats'])}:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,apad=whole_dur={silent_dur}[vo]"
    vo_filter = ";".join(filter_parts + [amix])

    vo_track = VO_DIR / "_vo_track.wav"
    print(f"[mix] building master VO track -> {vo_track.name}")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        *vo_inputs,
        "-filter_complex", vo_filter,
        "-map", "[vo]",
        "-c:a", "pcm_s16le",
        "-t", f"{silent_dur:.3f}",
        str(vo_track),
    ], check=True)

    # Step C: full mix — VO + sidechain-ducked music, then mux with silent video
    print(f"[mix] composing final mp4 -> {FINAL.name}")
    # Build a filter that:
    #   [1] = silent video's (absent) audio — we don't use it
    #   [2:a] = VO wav
    #   [3:a] = music
    # We bring VO and music in as two extra audio inputs.
    # music: trim to silent_dur, vol=0.06 (~-24 dB), fade-in 1.5 fade-out 2.5
    fade_out_start = max(silent_dur - 2.5, 0)
    audio_filter = (
        f"[1:a]volume=1.0,aformat=channel_layouts=stereo,asplit=2[vo_mix][vo_sc];"
        f"[2:a]atrim=0:{silent_dur:.3f},asetpts=PTS-STARTPTS,"
        f"volume=0.06,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start:.3f}:d=2.5,"
        f"aformat=channel_layouts=stereo[bed];"
        f"[bed][vo_sc]sidechaincompress=threshold=0.02:ratio=20:attack=8:release=350[ducked];"
        f"[vo_mix][ducked]amix=inputs=2:duration=longest:weights=1.0 0.55:normalize=0[mix]"
    )

    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
        "-i", str(SILENT),
        "-i", str(vo_track),
        "-i", str(MUSIC),
        "-filter_complex", audio_filter,
        "-map", "0:v",
        "-map", "[mix]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        str(FINAL),
    ], check=True)

    final_dur = probe_dur(FINAL)
    print(f"[done] {FINAL} duration={final_dur:.3f}s")
    if final_dur > 60.0:
        sys.exit(f"FAIL: final duration {final_dur:.2f}s exceeds 60s cap")

if __name__ == "__main__":
    main()
