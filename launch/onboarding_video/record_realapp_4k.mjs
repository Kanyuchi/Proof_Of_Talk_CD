/**
 * record_realapp_4k.mjs — REAL-APP onboarding capture at TRUE 4K (3840×2160).
 *
 * Why a new recorder: Playwright's `recordVideo` rasterizes at the `size` param
 * and IGNORES deviceScaleFactor, so the old pipeline captured 1280×720 then
 * upscaled to 1080p — soft text. This recorder instead drives the SAME 6-beat
 * flow (reusing the action sequence + the mid-run re-stage from
 * record_realapp.mjs) but captures crisp HIGH-DPI SCREENSHOT FRAMES:
 *
 *   viewport 1920×1080  +  deviceScaleFactor: 2   →  page.screenshot() = 3840×2160
 *
 * A background loop snaps frames as fast as it can across the whole run (so
 * motion + visible typing read smoothly), writing a numbered JPEG sequence to
 * frames4k/ AND recording each frame's wall-clock offset. 4K screenshots cost
 * ~85ms (JPEG q92), so the real capture rate is ~10fps, not 30 — so we DO NOT
 * play the sequence at a naive constant fps (that would compress the deliberate
 * pauses into a fast blur). Instead beats.json records each frame's real-time
 * offset, and assemble_realapp_4k.sh feeds ffmpeg a concat list with per-frame
 * durations → the output plays back at TRUE real time (pauses stay pauses,
 * typing stays smooth) and is re-timed to a constant 30fps container. JPEG q92
 * at 4K keeps UI text crisp while ~halving screenshot cost vs PNG (more frames
 * = smoother motion).
 *
 * Flow (real app, identical to record_realapp.mjs):
 *   1. Magic link -> set password (claim account) -> lands logged in
 *   2. Profile -> "Your write-up" -> Regenerate with AI -> tweak -> Save
 *   3. Matches -> hover top card -> Accept ("I'd like to meet") a pending match
 *   4. Messages -> open the pre-staged mutual thread (Thomas Weber) -> send a msg
 *   5. Booking -> click a "Both free at — tap to book" slot chip -> confirmed
 *   6. Threads -> open "Tokenisation & RWA" -> type a reply
 *
 * The demo identity (Alex Rivera, alex.video@demo.proofoftalk.io) and its
 * matches/thread are staged by backend/scripts/stage_onboarding_video_demo.py.
 * This script RE-RUNS that staging first (fresh magic token + re-armed claim),
 * then reads MAGIC_TOKEN= from its stdout, and re-stages matches mid-run after
 * the on-camera profile save (which fires refresh_profile_matches).
 *
 * Run from the repo root (Playwright lives in repo-root node_modules):
 *   NODE_PATH=/Users/kanyuchi/Developer/Proof_Of_Talk_CD/node_modules \
 *     node launch/onboarding_video/record_realapp_4k.mjs
 *
 * Output: launch/onboarding_video/frames4k/frame_000001.png ...  (3840×2160).
 * Assemble with assemble_realapp_4k.sh -> pot_onboarding_realapp_4k.mp4.
 */
import { chromium } from "playwright";
import { execSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..");
const BACKEND = join(REPO, "backend");
const FRAMES_DIR = join(__dirname, "frames4k");
const FRONT = process.env.FRONT_URL || "http://localhost:5173";
const PASSWORD = "Paris2026!";

const FPS = 30;                 // output container framerate (assembler target)

// ── helpers ──────────────────────────────────────────────────────────────────
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Stage the demo data and pull the fresh magic token out of stdout. */
function stageDemo() {
  console.log("[record4k] staging demo data (fresh token + re-armed claim)…");
  const out = execSync(
    "source .venv/bin/activate && python scripts/stage_onboarding_video_demo.py",
    { cwd: BACKEND, shell: "/bin/zsh", encoding: "utf8" }
  );
  process.stdout.write(out);
  const m = out.match(/MAGIC_TOKEN=([A-Za-z0-9_\-]+)/);
  if (!m) throw new Error("could not parse MAGIC_TOKEN from staging output");
  return m[1];
}

/** Rebuild ONLY the demo matches (post-save refresh wiped them). */
function restageMatches() {
  console.log("[record4k] re-staging demo matches (post-save refresh wiped them)…");
  const out = execSync(
    "source .venv/bin/activate && python scripts/stage_onboarding_video_demo.py --matches-only",
    { cwd: BACKEND, shell: "/bin/zsh", encoding: "utf8" }
  );
  process.stdout.write(out);
}

/**
 * Continuous high-DPI frame grabber. Snaps page.screenshot() as fast as it can
 * into frames4k/frame_NNNNNN.jpg. Because the context has deviceScaleFactor:2
 * over a 1920×1080 viewport, each JPEG is 3840×2160.
 *
 * Records each frame's wall-clock offset into `this.times[]`, EXCLUDING any
 * paused interval (stop→start gap, e.g. the off-camera re-stage). The assembler
 * uses those offsets to play frames back at true real time at a constant 30fps
 * container — so deliberate pauses + visible typing read naturally instead of
 * being compressed by a naive constant-fps assumption.
 */
class FrameGrabber {
  constructor(page, dir) {
    this.page = page;
    this.dir = dir;
    this.n = 0;
    this.running = false;
    this._loop = null;
    this.times = [];      // monotonic on-camera offset (s) per captured frame
    this._elapsed = 0;    // accumulated on-camera time across start/stop cycles
    this._segStart = 0;   // wall ms when the current capture segment started
  }
  start() {
    this.running = true;
    this._segStart = Date.now();
    this._loop = (async () => {
      while (this.running) {
        const t0 = Date.now();
        const idx = String(this.n + 1).padStart(6, "0");
        try {
          await this.page.screenshot({
            path: join(this.dir, `frame_${idx}.jpg`),
            type: "jpeg",
            quality: 92,
            animations: "allow",
            caret: "hide",
          });
          this.n++;
          // On-camera offset = time already banked + time into this segment.
          const offset = this._elapsed + (Date.now() - this._segStart) / 1000;
          this.times.push(+offset.toFixed(4));
        } catch (e) {
          // page mid-navigation can throw; skip this tick, keep going.
        }
        // No artificial delay — capture as fast as 4K JPEG encode allows.
      }
    })();
  }
  async stop() {
    this.running = false;
    if (this._loop) await this._loop;
    // Bank this segment's on-camera duration so the next segment continues from
    // where this one left off (the paused gap is excluded from the timeline).
    this._elapsed += (Date.now() - this._segStart) / 1000;
    return this.n;
  }
}

async function main() {
  const token = stageDemo();
  // Fresh frame dir each run.
  rmSync(FRAMES_DIR, { recursive: true, force: true });
  mkdirSync(FRAMES_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2, // → page.screenshot() yields 3840×2160 sharp PNGs
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  const grabber = new FrameGrabber(page, FRAMES_DIR);

  // Beat markers: on-camera timestamp at the moment each beat begins. Uses the
  // grabber's last recorded frame offset (real-time, paused gaps excluded) so
  // captions land exactly over the right segment in the assembled video.
  const beats = [];
  const mark = (label) => {
    const t = grabber.times.length ? grabber.times[grabber.times.length - 1] : 0;
    beats.push({ label, frame: grabber.n, t });
    console.log(`[record4k] BEAT MARK ${label} @ frame ${grabber.n} (t=${t}s)`);
  };

  try {
    // ── BEAT 1 — Magic link -> set password (claim) ────────────────────────
    console.log("[record4k] beat 1: magic link -> set password");
    await page.goto(`${FRONT}/m/${token}?unlock=1`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Set your password" }).waitFor();
    // Start grabbing only once the first real screen is painted.
    grabber.start();
    mark("beat1");
    await sleep(1800);

    const pwd = page.locator('input[type="password"]').first();
    await pwd.scrollIntoViewIfNeeded();
    await pwd.click();
    await pwd.type(PASSWORD, { delay: 70 });
    await sleep(1200);
    await page.getByRole("button", { name: /create my account/i }).click();
    await page.waitForURL("**/matches", { timeout: 30000 });
    await page.waitForLoadState("networkidle");
    await sleep(1600);

    // ── BEAT 2 — Profile / write-up / Regenerate with AI / Save ────────────
    console.log("[record4k] beat 2: profile write-up + regenerate + save");
    mark("beat2");
    await page.goto(`${FRONT}/profile`, { waitUntil: "networkidle" });
    await sleep(1200);
    const writeupHeading = page.getByRole("heading", { name: /your write-up/i });
    await writeupHeading.scrollIntoViewIfNeeded();
    await sleep(1000);

    const textarea = page.getByPlaceholder(/how you're introduced to your matches/i);
    const before = (await textarea.inputValue()) || "";

    await page.getByRole("button", { name: /regenerate with ai/i }).click();
    await page.waitForFunction(
      (prev) => {
        const t = document.querySelector(
          'textarea[placeholder*="introduced to your matches"]'
        );
        return t && t.value && t.value.trim().length > 30 && t.value !== prev;
      },
      before,
      { timeout: 30000 }
    );
    await sleep(1400);

    await textarea.scrollIntoViewIfNeeded();
    await textarea.click();
    await page.keyboard.press("End");
    await textarea.type("  Building in public at Proof of Talk.", { delay: 45 });
    await sleep(1100);

    await page.getByRole("button", { name: /save changes/i }).click();
    await page.getByText(/profile saved successfully/i).waitFor({ timeout: 20000 });
    await sleep(2200);

    // The save fired a detached refresh_profile_matches that regenerates Alex's
    // matches against the REAL pool — wiping the curated demo set + the mutual
    // Thomas thread. Pause the grabber while we wait + re-stage (off camera).
    await grabber.stop();
    await sleep(6000); // let the detached re-embed + match-regen settle
    restageMatches();
    await sleep(500);
    grabber.start();

    // ── BEAT 3 — Matches -> hover top card -> Accept ───────────────────────
    console.log("[record4k] beat 3: matches -> hover -> accept");
    mark("beat3");
    await page.goto(`${FRONT}/matches`, { waitUntil: "networkidle" });
    await sleep(1600);
    const firstCard = page.locator('[class*="rounded-2xl"]').filter({ hasText: /complementary|deal-ready|non-obvious|match/i }).first();
    try {
      await firstCard.scrollIntoViewIfNeeded();
      await firstCard.hover();
    } catch { /* hover is cosmetic */ }
    await sleep(1300);

    const acceptBtn = page.getByRole("button", { name: /i'd like to meet/i }).first();
    await acceptBtn.scrollIntoViewIfNeeded();
    await sleep(600);
    await acceptBtn.click();
    await page.getByText(/you accepted|waiting for/i).first().waitFor({ timeout: 20000 });
    await sleep(1800);

    // ── BEAT 4 — Messages -> open mutual thread -> send message ────────────
    console.log("[record4k] beat 4: messages -> open mutual -> send");
    mark("beat4");
    await page.goto(`${FRONT}/messages`, { waitUntil: "networkidle" });
    await sleep(1400);
    const conv = page.getByText(/thomas weber/i).first();
    await conv.scrollIntoViewIfNeeded();
    await conv.click();
    await sleep(1300);
    const composer = page.getByPlaceholder(/type a message/i);
    await composer.waitFor({ timeout: 15000 });
    await composer.click();
    await composer.type(
      "Thomas — would love to walk you through a tokenised private-credit product for Hanseatic's IC. Coffee on June 2?",
      { delay: 32 }
    );
    await sleep(900);
    await composer.press("Enter").catch(async () => {
      await page.locator("button").filter({ has: page.locator("svg") }).last().click();
    });
    await page.getByText(/tokenised private-credit|Hanseatic's IC/i).first().waitFor({ timeout: 15000 });
    await sleep(1800);

    // ── BEAT 5 — Booking -> "Both free at — tap to book" slot chip ─────────
    console.log("[record4k] beat 5: booking a free slot");
    mark("beat5");
    await page.goto(`${FRONT}/matches`, { waitUntil: "networkidle" });
    await sleep(1400);
    const bookLabel = page.getByText(/both free at — tap to book/i).first();
    let booked = false;
    try {
      await bookLabel.scrollIntoViewIfNeeded({ timeout: 8000 });
      await sleep(900);
      const chip = bookLabel.locator("xpath=following::button[1]");
      await chip.click();
      await page.getByText(/add to calendar/i).first().waitFor({ timeout: 15000 });
      booked = true;
      await sleep(1900);
    } catch (e) {
      console.warn("[record4k] booking via chip failed, trying 'Save a preferred time'…", e.message);
      try {
        const seeAll = page.getByRole("button", { name: /see all times|save a preferred time/i }).first();
        await seeAll.scrollIntoViewIfNeeded();
        await seeAll.click();
        await sleep(900);
        const timeBtn = page.locator("button.font-mono").first();
        await timeBtn.click();
        await sleep(700);
        await page.getByRole("button", { name: /^save /i }).first().click();
        await page.getByText(/add to calendar/i).first().waitFor({ timeout: 15000 });
        booked = true;
        await sleep(1800);
      } catch (e2) {
        console.warn("[record4k] booking fallback also failed:", e2.message);
      }
    }
    console.log("[record4k] booking captured:", booked);

    // ── BEAT 6 — Threads -> open -> type a reply ───────────────────────────
    console.log("[record4k] beat 6: threads -> open -> reply");
    mark("beat6");
    await page.goto(`${FRONT}/threads`, { waitUntil: "networkidle" });
    await sleep(1400);
    const threadCard = page.getByText(/builders circle/i).first();
    await threadCard.scrollIntoViewIfNeeded();
    await threadCard.click();
    await sleep(1300);
    const reply = page.getByPlaceholder(/share a thought with the group/i);
    await reply.waitFor({ timeout: 15000 });
    await reply.click();
    await reply.type(
      "Custody is the bottleneck for us too — building tokenisation rails that plug into regulated custody from day one. Keen to compare notes.",
      { delay: 30 }
    );
    await sleep(900);
    await reply.press("Enter");
    await page.getByText(/custody is the bottleneck for us too/i).first().waitFor({ timeout: 15000 });
    await sleep(2200);

    console.log("[record4k] flow complete — stopping grabber");
  } finally {
    const total = await grabber.stop();
    console.log(`[record4k] captured ${total} frames`);
    await page.close();
    await context.close();
    await browser.close();
  }

  // Persist beat markers + per-frame on-camera offsets for the assembler. The
  // assembler builds a concat list from frame_times so playback is real-time at
  // a constant 30fps container.
  const onCameraDuration = grabber.times.length ? grabber.times[grabber.times.length - 1] : 0;
  const markers = {
    fps: FPS,
    ext: "jpg",
    frame_count: grabber.n,
    duration_s: +onCameraDuration.toFixed(3),
    beats,                       // each {label, frame, t(seconds)}
    frame_times: grabber.times,  // on-camera offset (s) per frame, 1-indexed
  };
  const markersPath = join(FRAMES_DIR, "beats.json");
  writeFileSync(markersPath, JSON.stringify(markers, null, 2));
  console.log(`[record4k] wrote beat markers -> ${markersPath}`);

  console.log(`FRAMES_DIR=${FRAMES_DIR}`);
  console.log(`FRAME_COUNT=${grabber.n}`);
  console.log(`DURATION_S=${onCameraDuration.toFixed(2)}`);
}

main().catch((e) => {
  console.error("[record4k] FAILED:", e);
  process.exit(1);
});
