// smoke.mjs — boot the page, confirm __renderReady, capture 4 scene screenshots.
import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER = 'http://localhost:8765/?render=1';
const W = 1920, H = 1080;

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

await page.goto(SERVER, { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__renderReady === true, { timeout: 30_000 });
const ready = await page.evaluate(() => window.__renderReady === true);
const dur = await page.evaluate(() => window.__getDuration());
console.log('__renderReady =', ready, '| duration =', dur);

await page.addStyleTag({ content: `
  .stage-wrap > div { width: 100vw !important; height: 100vh !important; }
  [data-render-canvas] { transform: none !important; width: ${W}px !important; height: ${H}px !important; }
` });

const shots = [
  [2.0,  'smoke_t02_title.png'],
  [34.0, 'smoke_t34_mutual.png'],
  [48.0, 'smoke_t48_threads.png'],
  [58.0, 'smoke_t58_cta.png'],
];
for (const [t, name] of shots) {
  await page.evaluate((tt) => window.__seek(tt), t);
  await page.waitForTimeout(120);
  await page.screenshot({ path: path.join(__dirname, name), clip: { x: 0, y: 0, width: W, height: H } });
  console.log('captured', name, 'at t=' + t);
}

await browser.close();
if (errors.length) {
  console.log('\n--- CONSOLE ERRORS (' + errors.length + ') ---');
  errors.slice(0, 20).forEach(e => console.log(e));
} else {
  console.log('\nNo console/page errors.');
}
