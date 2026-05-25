/**
 * record_realapp.mjs — REAL-APP onboarding screen recording.
 *
 * Drives the actual POT Matchmaker UI (React app on :5173, FastAPI on :8000,
 * pointed at the prod Supabase DB) through the real onboarding flow with
 * Playwright, recording the whole run to a single continuous .webm via a
 * browser context with recordVideo.
 *
 * Flow (real app, in order):
 *   1. Magic link -> set password (claim account) -> lands logged in
 *   2. Profile -> "Your write-up" -> Regenerate with AI -> tweak -> Save
 *   3. Matches -> hover top card -> Accept ("I'd like to meet") a pending match
 *   4. Messages -> open the pre-staged mutual thread (Thomas Weber) -> send a msg
 *   5. Booking -> click a "Both free at — tap to book" slot chip -> confirmed
 *   6. Threads -> open "Tokenisation & RWA" -> type a reply
 *
 * The demo identity (Alex Rivera, alex.video@demo.proofoftalk.io) and its
 * matches/thread are staged by backend/scripts/stage_onboarding_video_demo.py.
 * This script RE-RUNS that staging first (to get a fresh magic token and re-arm
 * the claim flow), then reads MAGIC_TOKEN= from its stdout.
 *
 * Run from the repo root (Playwright lives in repo-root node_modules):
 *   NODE_PATH=/Users/kanyuchi/Developer/Proof_Of_Talk_CD/node_modules \
 *     node launch/onboarding_video/record_realapp.mjs
 *
 * Output: launch/onboarding_video/raw/<auto>.webm  (path printed at the end as
 * RAW_WEBM=...). Assemble with assemble_realapp.sh.
 */
import { chromium } from "playwright";
import { execSync } from "node:child_process";
import { mkdirSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..");
const BACKEND = join(REPO, "backend");
const RAW_DIR = join(__dirname, "raw");
const FRONT = process.env.FRONT_URL || "http://localhost:5173";
const PASSWORD = "Paris2026!";

// ── helpers ──────────────────────────────────────────────────────────────────
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Stage the demo data and pull the fresh magic token out of stdout. */
function stageDemo() {
  console.log("[record] staging demo data (fresh token + re-armed claim)…");
  const out = execSync(
    "source .venv/bin/activate && python scripts/stage_onboarding_video_demo.py",
    { cwd: BACKEND, shell: "/bin/zsh", encoding: "utf8" }
  );
  process.stdout.write(out);
  const m = out.match(/MAGIC_TOKEN=([A-Za-z0-9_\-]+)/);
  if (!m) throw new Error("could not parse MAGIC_TOKEN from staging output");
  return m[1];
}

/**
 * Rebuild ONLY the demo matches. The real app's profile-save handler fires a
 * detached `refresh_profile_matches`, which regenerates Alex's matches against
 * the REAL attendee pool — wiping the curated demo set + the mutual Thomas
 * thread. We call this AFTER the on-camera Save (and after a wait for that
 * detached task to settle) so the rest of the flow stays demo-safe.
 */
function restageMatches() {
  console.log("[record] re-staging demo matches (post-save refresh wiped them)…");
  const out = execSync(
    "source .venv/bin/activate && python scripts/stage_onboarding_video_demo.py --matches-only",
    { cwd: BACKEND, shell: "/bin/zsh", encoding: "utf8" }
  );
  process.stdout.write(out);
}

/** Newest file in a dir (used to find the recorded webm). */
function newestFile(dir) {
  const files = readdirSync(dir)
    .map((f) => join(dir, f))
    .filter((p) => statSync(p).isFile());
  files.sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
  return files[0];
}

async function main() {
  const token = stageDemo();
  mkdirSync(RAW_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 2,
    recordVideo: { dir: RAW_DIR, size: { width: 1280, height: 720 } },
    // Skip CSS animations? No — keep them, they read as "real app".
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);

  try {
    // ── BEAT 1 — Magic link -> set password (claim) ────────────────────────
    console.log("[record] beat 1: magic link -> set password");
    await page.goto(`${FRONT}/m/${token}?unlock=1`, { waitUntil: "networkidle" });
    // The claim panel is pre-opened by ?unlock=1 and scrolled into view.
    await page.getByRole("heading", { name: "Set your password" }).waitFor();
    await sleep(1800);

    const pwd = page.locator('input[type="password"]').first();
    await pwd.scrollIntoViewIfNeeded();
    await pwd.click();
    await pwd.type(PASSWORD, { delay: 70 });
    await sleep(1200);
    await page.getByRole("button", { name: /create my account/i }).click();
    // Claim succeeds -> hard nav to /matches.
    await page.waitForURL("**/matches", { timeout: 30000 });
    await page.waitForLoadState("networkidle");
    await sleep(1600);

    // ── BEAT 2 — Profile / write-up / Regenerate with AI / Save ────────────
    console.log("[record] beat 2: profile write-up + regenerate + save");
    await page.goto(`${FRONT}/profile`, { waitUntil: "networkidle" });
    await sleep(1200);
    // Scroll to the "Your write-up" section.
    const writeupHeading = page.getByRole("heading", { name: /your write-up/i });
    await writeupHeading.scrollIntoViewIfNeeded();
    await sleep(1000);

    // The write-up textarea is uniquely identified by its placeholder
    // ("How you're introduced to your matches…") — there are other textareas
    // (Goals, "Who do you want to meet?") on the page.
    const textarea = page.getByPlaceholder(/how you're introduced to your matches/i);
    const before = (await textarea.inputValue()) || "";

    // Click "Regenerate with AI" — real OpenAI call fills the textarea.
    await page.getByRole("button", { name: /regenerate with ai/i }).click();
    // Wait until the write-up textarea content changes (the draft arrives).
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

    // Tweak a word: append a short phrase so the edit is visible on camera.
    await textarea.scrollIntoViewIfNeeded();
    await textarea.click();
    await page.keyboard.press("End");
    await textarea.type("  Building in public at Proof of Talk.", { delay: 45 });
    await sleep(1100);

    // Save -> green "Profile saved successfully." confirmation.
    await page.getByRole("button", { name: /save changes/i }).click();
    await page.getByText(/profile saved successfully/i).waitFor({ timeout: 20000 });
    await sleep(2200);

    // The save fired a detached `refresh_profile_matches` that regenerates
    // Alex's matches against the REAL pool — wiping our demo set + the mutual
    // Thomas thread. Give that detached task time to land, THEN re-stage the
    // demo-only matches so beats 3-5 stay demo-safe.
    await sleep(6000); // let the detached re-embed + match-regen settle
    restageMatches();
    await sleep(500);

    // ── BEAT 3 — Matches -> hover top card -> Accept ───────────────────────
    console.log("[record] beat 3: matches -> hover -> accept");
    await page.goto(`${FRONT}/matches`, { waitUntil: "networkidle" });
    await sleep(1600);
    // Hover the first match card to show interactivity.
    const firstCard = page.locator('[class*="rounded-2xl"]').filter({ hasText: /complementary|deal-ready|non-obvious|match/i }).first();
    try {
      await firstCard.scrollIntoViewIfNeeded();
      await firstCard.hover();
    } catch { /* hover is cosmetic */ }
    await sleep(1300);

    // Accept a pending match: the green "I'd like to meet" button.
    const acceptBtn = page.getByRole("button", { name: /i'd like to meet/i }).first();
    await acceptBtn.scrollIntoViewIfNeeded();
    await sleep(600);
    await acceptBtn.click();
    // The button is replaced by "You accepted — waiting for …" state.
    await page.getByText(/you accepted|waiting for/i).first().waitFor({ timeout: 20000 });
    await sleep(1800);

    // ── BEAT 4 — Messages -> open mutual thread -> send message ────────────
    console.log("[record] beat 4: messages -> open mutual -> send");
    await page.goto(`${FRONT}/messages`, { waitUntil: "networkidle" });
    await sleep(1400);
    // Open the (pre-staged mutual) Thomas Weber conversation.
    const conv = page.getByText(/thomas weber/i).first();
    await conv.scrollIntoViewIfNeeded();
    await conv.click();
    await sleep(1300);
    // The composer is ENABLED only for mutual matches.
    const composer = page.getByPlaceholder(/type a message/i);
    await composer.waitFor({ timeout: 15000 });
    await composer.click();
    await composer.type(
      "Thomas — would love to walk you through a tokenised private-credit product for Hanseatic's IC. Coffee on June 2?",
      { delay: 32 }
    );
    await sleep(900);
    // Send (the orange send button next to the input).
    await composer.press("Enter").catch(async () => {
      // fallback: click the send button
      await page.locator("button").filter({ has: page.locator("svg") }).last().click();
    });
    // Wait for the sent bubble to appear.
    await page.getByText(/tokenised private-credit|Hanseatic's IC/i).first().waitFor({ timeout: 15000 });
    await sleep(1800);

    // ── BEAT 5 — Booking -> "Both free at — tap to book" slot chip ─────────
    console.log("[record] beat 5: booking a free slot");
    await page.goto(`${FRONT}/matches`, { waitUntil: "networkidle" });
    await sleep(1400);
    // Find the mutual match's slot chips.
    const bookLabel = page.getByText(/both free at — tap to book/i).first();
    let booked = false;
    try {
      await bookLabel.scrollIntoViewIfNeeded({ timeout: 8000 });
      await sleep(900);
      // The chips are the buttons right under that label, formatted like "Mon 11:30".
      const chip = bookLabel.locator("xpath=following::button[1]");
      await chip.click();
      // Confirmed -> the card shows the booked meeting time + "Add to Calendar".
      await page.getByText(/add to calendar/i).first().waitFor({ timeout: 15000 });
      booked = true;
      await sleep(1900);
    } catch (e) {
      console.warn("[record] booking via chip failed, trying 'Save a preferred time'…", e.message);
      try {
        const seeAll = page.getByRole("button", { name: /see all times|save a preferred time/i }).first();
        await seeAll.scrollIntoViewIfNeeded();
        await seeAll.click();
        await sleep(900);
        // pick first available slot time button, then save
        const timeBtn = page.locator("button.font-mono").first();
        await timeBtn.click();
        await sleep(700);
        await page.getByRole("button", { name: /^save /i }).first().click();
        await page.getByText(/add to calendar/i).first().waitFor({ timeout: 15000 });
        booked = true;
        await sleep(1800);
      } catch (e2) {
        console.warn("[record] booking fallback also failed:", e2.message);
      }
    }
    console.log("[record] booking captured:", booked);

    // ── BEAT 6 — Threads -> open -> type a reply ───────────────────────────
    console.log("[record] beat 6: threads -> open -> reply");
    await page.goto(`${FRONT}/threads`, { waitUntil: "networkidle" });
    await sleep(1400);
    // Open the seeded DEMO-ONLY thread ("Tokenisation & RWA — Builders Circle").
    // This thread contains only demo-persona posts, so no real attendee name
    // appears on camera (the public default threads mix real + demo authors).
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

    console.log("[record] flow complete — closing context to flush video");
  } finally {
    // Closing the page+context flushes the .webm to disk.
    await page.close();
    await context.close();
    await browser.close();
  }

  const webm = newestFile(RAW_DIR);
  console.log(`RAW_WEBM=${webm}`);
}

main().catch((e) => {
  console.error("[record] FAILED:", e);
  process.exit(1);
});
