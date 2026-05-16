#!/usr/bin/env node
// render.mjs — record the browser-rendered video to MP4 (1080p or 4K).
//
// Run from launch/our_version/:
//   1. Make sure the dev server is running:  python3 -m http.server 8765
//   2. node render.mjs               → 1920×1080 60fps MP4 (~76s)
//      node render.mjs --4k          → 3840×2160 60fps MP4 (4× the data, ~10min render)
//      node render.mjs --fps=30      → halve frame count (faster, less smooth)
//
// Output: pot_matchmaker_v1.mp4 in the same directory.
//
// Requirements (one-time):
//   npm install --no-save playwright
//   npx playwright install chromium
//   ffmpeg installed (brew install ffmpeg)

import { chromium } from 'playwright';
import { spawn, spawnSync } from 'child_process';
import { mkdirSync, rmSync, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── flags ────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const is4K   = args.includes('--4k');
const fps    = parseInt((args.find(a => a.startsWith('--fps=')) || '--fps=60').split('=')[1], 10);
const SERVER = 'http://localhost:8765/?render=1';
const DUR    = 76.30;
const W      = is4K ? 3840 : 1920;
const H      = is4K ? 2160 : 1080;
const FRAMES_DIR = path.join(__dirname, '.render_frames');
const OUT_VIDEO  = path.join(__dirname, is4K ? 'pot_matchmaker_4k.mp4' : 'pot_matchmaker_1080p.mp4');

console.log(`[render] target: ${W}×${H} @ ${fps}fps, duration ${DUR}s`);
console.log(`[render] frames will be saved to ${FRAMES_DIR}`);
console.log(`[render] final MP4: ${OUT_VIDEO}\n`);

// Reset frames dir
if (existsSync(FRAMES_DIR)) rmSync(FRAMES_DIR, { recursive: true });
mkdirSync(FRAMES_DIR);

// ── render ───────────────────────────────────────────────────────────────────
const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: 1, // exact pixel match
});
const page = await ctx.newPage();

console.log('[render] loading page…');
await page.goto(SERVER, { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__renderReady === true, { timeout: 30_000 });

// Ensure the Stage scales to the full viewport (override default letterbox)
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
const args_ffmpeg = [
  '-y',
  '-framerate', String(fps),
  '-i', path.join(FRAMES_DIR, 'f_%05d.png'),
  '-i', path.join(__dirname, 'voiceover.mp3'),
  '-i', path.join(__dirname, 'music.mp3'),
  '-filter_complex',
    `[1:a]volume=1.0[vo];` +
    `[2:a]volume=0.28[mus];` +
    `[vo][mus]amix=inputs=2:duration=longest:normalize=0[a]`,
  '-map', '0:v',
  '-map', '[a]',
  '-c:v', 'libx264',
  '-pix_fmt', 'yuv420p',
  '-preset', 'slow',
  '-crf', is4K ? '20' : '18',
  '-r', String(fps),
  '-c:a', 'aac',
  '-b:a', '192k',
  '-t', String(DUR),
  '-movflags', '+faststart', // optimize for streaming
  OUT_VIDEO,
];

// Use spawnSync with arg array — avoids shell parsing of special chars like ; [ ]
// in the filter_complex expression.
const ff = spawnSync('ffmpeg', args_ffmpeg, { stdio: 'inherit' });
if (ff.status !== 0) {
  console.error(`\n[render] ffmpeg failed with exit code ${ff.status}`);
  process.exit(ff.status ?? 1);
}

// Cleanup intermediate frames (comment out if you want to keep them)
rmSync(FRAMES_DIR, { recursive: true });

console.log(`\n[render] ✅ done: ${OUT_VIDEO}`);
console.log(`[render] inspect: ffprobe "${OUT_VIDEO}"`);
console.log(`[render] play:    open "${OUT_VIDEO}"`);
