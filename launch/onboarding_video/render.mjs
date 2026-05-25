#!/usr/bin/env node
// render.mjs — record the browser-rendered ONBOARDING video to MP4 (1080p / 4K).
//
// Run from launch/onboarding_video/:
//   1. Start the dev server:  python3 -m http.server 8765
//   2. node render.mjs               → 1920×1080 60fps MP4 (~60s)
//      node render.mjs --4k          → 3840×2160 60fps MP4 (4× the data)
//      node render.mjs --fps=30      → halve the frame count (faster preview)
//
// Output: pot_onboarding_1080p.mp4 in this directory.
//
// Requirements (one-time):
//   npm install --no-save playwright      (already installed at repo root)
//   npx playwright install chromium
//   ffmpeg installed (brew install ffmpeg)
//
// AUDIO: this onboarding cut has NO voiceover yet (VO needs ElevenLabs — out of
// scope for this pass), so we mux MUSIC ONLY at a gentle bed level.
// TODO: add voiceover.mp3 (ElevenLabs) and restore the VO mux — see commented
//       branch in the ffmpeg filter below.

import { chromium } from 'playwright';
import { spawnSync } from 'child_process';
import { mkdirSync, rmSync, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── flags ────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const is4K = args.includes('--4k');
const fps  = parseInt((args.find(a => a.startsWith('--fps=')) || '--fps=60').split('=')[1], 10);
const SERVER = 'http://localhost:8765/?render=1';
const DUR = 60.0;
const W = is4K ? 3840 : 1920;
const H = is4K ? 2160 : 1080;
const FRAMES_DIR = path.join(__dirname, '.render_frames');
const OUT_VIDEO  = path.join(__dirname, is4K ? 'pot_onboarding_4k.mp4' : 'pot_onboarding_1080p.mp4');
const MUSIC = path.join(__dirname, 'music.mp3');
const hasMusic = existsSync(MUSIC);

console.log(`[render] target: ${W}×${H} @ ${fps}fps, duration ${DUR}s`);
console.log(`[render] frames -> ${FRAMES_DIR}`);
console.log(`[render] final MP4 -> ${OUT_VIDEO}`);
console.log(`[render] audio: ${hasMusic ? 'music only (no VO yet)' : 'SILENT (music.mp3 missing)'}\n`);

// Reset frames dir
if (existsSync(FRAMES_DIR)) rmSync(FRAMES_DIR, { recursive: true });
mkdirSync(FRAMES_DIR);

// ── render ───────────────────────────────────────────────────────────────────
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

console.log('[render] loading page…');
await page.goto(SERVER, { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__renderReady === true, { timeout: 30_000 });

// Force the Stage to fill the viewport at 1:1 (override the default letterbox).
await page.addStyleTag({ content: `
  .stage-wrap > div { width: 100vw !important; height: 100vh !important; }
  [data-render-canvas] { transform: none !important; width: ${W}px !important; height: ${H}px !important; }
` });

const totalFrames = Math.round(DUR * fps);
const frameStep = 1 / fps;
console.log(`[render] capturing ${totalFrames} frames…`);

const start = Date.now();
for (let i = 0; i < totalFrames; i++) {
  const t = i * frameStep;
  await page.evaluate((tt) => window.__seek(tt), t);
  await page.waitForTimeout(20); // give React 1 tick to render
  const fname = path.join(FRAMES_DIR, `f_${String(i).padStart(5, '0')}.png`);
  await page.screenshot({ path: fname, omitBackground: false, clip: { x: 0, y: 0, width: W, height: H } });
  if (i % 60 === 0) {
    const pct = ((i / totalFrames) * 100).toFixed(1);
    const elapsed = ((Date.now() - start) / 1000).toFixed(0);
    process.stdout.write(`\r[render] frame ${i}/${totalFrames} (${pct}%) — ${elapsed}s elapsed`);
  }
}
console.log(`\n[render] capture done in ${((Date.now() - start) / 1000).toFixed(0)}s`);

await browser.close();

// ── mux frames + audio via ffmpeg ────────────────────────────────────────────
console.log('[render] muxing frames + audio with ffmpeg…');

const baseArgs = [
  '-y',
  '-framerate', String(fps),
  '-i', path.join(FRAMES_DIR, 'f_%05d.png'),
];

let audioArgs;
if (hasMusic) {
  // Music-only bed at a gentle level. When VO lands, switch to the commented
  // two-input mix below and add  '-i', voiceover.mp3  before music.
  //
  //   const voArgs = [
  //     '-i', voiceover.mp3, '-i', music.mp3,
  //     '-filter_complex',
  //       `[1:a]volume=1.0[vo];[2:a]volume=0.28[mus];` +
  //       `[vo][mus]amix=inputs=2:duration=longest:normalize=0[a]`,
  //     '-map', '0:v', '-map', '[a]',
  //   ];
  audioArgs = [
    '-i', MUSIC,
    '-filter_complex', `[1:a]volume=0.22,afade=t=in:st=0:d=2.0,afade=t=out:st=${(DUR - 3.0).toFixed(2)}:d=3.0[a]`,
    '-map', '0:v', '-map', '[a]',
    '-c:a', 'aac', '-b:a', '192k',
  ];
} else {
  // No music available — render silent.
  audioArgs = ['-map', '0:v'];
}

const tailArgs = [
  '-c:v', 'libx264',
  '-pix_fmt', 'yuv420p',
  '-preset', 'slow',
  '-crf', is4K ? '20' : '18',
  '-r', String(fps),
  '-t', String(DUR),
  '-movflags', '+faststart',
  OUT_VIDEO,
];

const ffmpegArgs = [...baseArgs, ...audioArgs, ...tailArgs];
const ff = spawnSync('ffmpeg', ffmpegArgs, { stdio: 'inherit' });
if (ff.status !== 0) {
  console.error(`\n[render] ffmpeg failed with exit code ${ff.status}`);
  process.exit(ff.status ?? 1);
}

// Cleanup intermediate frames (comment out to keep them).
rmSync(FRAMES_DIR, { recursive: true });

console.log(`\n[render] done: ${OUT_VIDEO}`);
console.log(`[render] inspect: ffprobe "${OUT_VIDEO}"`);
console.log(`[render] play:    open "${OUT_VIDEO}"`);
