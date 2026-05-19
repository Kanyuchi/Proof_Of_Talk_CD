"""
Diagnose photo extraction for a single LinkedIn profile.

Opens a Playwright browser, waits for the operator to log in to LinkedIn,
navigates to the given profile URL, and dumps every image-like element
inside <main> with its src / srcset / data-delayed-url / alt / aria-label,
plus the closest-common-ancestor distance to the profile owner's <h1>.

Intended as a one-shot tool to figure out which markup pattern a stubborn
profile's photo actually uses, before extending the production selector in
linkedin_scrape.py.

Usage:
    python scripts/diagnose_photo_dom.py "https://www.linkedin.com/in/<slug>/"
"""

import argparse
import asyncio
import json
import sys


async def diagnose(url: str) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        print("Opening LinkedIn login page...")
        print("➡️  Log in manually in the browser window (incl. 2FA).")
        await page.goto("https://www.linkedin.com/login", timeout=30000)

        logged_in = False
        for _ in range(60):
            await page.wait_for_timeout(3000)
            cur = page.url
            if "/feed" in cur or "/mynetwork" in cur or "/messaging" in cur:
                logged_in = True
                break
        if not logged_in:
            print("Login timed out.")
            await browser.close()
            return
        print("Logged in ✅\n")

        print(f"Navigating to: {url}")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        # Settle: scroll, wait, scroll back. The production scraper does the
        # same dance so the DOM here matches what production sees.
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        await page.wait_for_timeout(1500)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1500)

        result = await page.evaluate(
            r"""() => {
            const main = document.querySelector('main') || document.body;
            const h1 = main.querySelector('h1');

            // Walk up from `el` to the closest ancestor that contains `target`.
            // Returns {depth, ancestorTag} or {depth:-1} if not found.
            function depthToShared(el, target) {
                if (!el || !target) return { depth: -1, ancestorTag: null };
                let node = el;
                let depth = 0;
                while (node && !node.contains(target)) {
                    node = node.parentElement;
                    depth++;
                    if (depth > 30) return { depth: -1, ancestorTag: null };
                }
                return {
                    depth,
                    ancestorTag: node ? node.tagName.toLowerCase() : null,
                    ancestorClass: node ? (node.className || '').toString().slice(0, 80) : null,
                };
            }

            const navSel = ['header img', 'nav img', '.global-nav img', '#global-nav img'];
            const navSrcs = new Set();
            navSel.forEach(s => document.querySelectorAll(s).forEach(i => i.src && navSrcs.add(i.src)));

            // All img elements in main
            const imgs = [...main.querySelectorAll('img')].map(img => {
                const d = depthToShared(img, h1);
                return {
                    kind: 'img',
                    src: img.src || null,
                    srcset: img.getAttribute('srcset'),
                    dataDelayedUrl: img.getAttribute('data-delayed-url'),
                    dataLiSrc: img.getAttribute('data-li-src'),
                    alt: img.getAttribute('alt'),
                    ariaLabel: img.getAttribute('aria-label'),
                    cls: (img.className || '').toString().slice(0, 120),
                    width: img.naturalWidth || img.width || null,
                    height: img.naturalHeight || img.height || null,
                    inNavBlacklist: navSrcs.has(img.src),
                    depthToH1: d.depth,
                    sharedAncestor: d.ancestorTag,
                    sharedAncestorClass: d.ancestorClass,
                };
            });

            // All picture>source elements in main (rare but possible)
            const sources = [...main.querySelectorAll('picture source')].map(src => {
                const d = depthToShared(src, h1);
                return {
                    kind: 'source',
                    srcset: src.getAttribute('srcset'),
                    media: src.getAttribute('media'),
                    type: src.getAttribute('type'),
                    depthToH1: d.depth,
                    sharedAncestor: d.ancestorTag,
                    sharedAncestorClass: d.ancestorClass,
                };
            });

            // Anything with profile-displayphoto / profile-framedphoto anywhere
            // in any attribute, across the WHOLE document (catches lazy attrs).
            const allEls = [...document.querySelectorAll('*')];
            const wildHits = [];
            for (const el of allEls) {
                for (const attr of el.attributes || []) {
                    const v = attr.value || '';
                    if (v.includes('profile-displayphoto') || v.includes('profile-framedphoto')) {
                        wildHits.push({
                            tag: el.tagName.toLowerCase(),
                            attr: attr.name,
                            value: v.slice(0, 200),
                            cls: (el.className || '').toString().slice(0, 80),
                        });
                        break; // one entry per element
                    }
                }
                if (wildHits.length >= 40) break;
            }

            // Capture the outer HTML of the closest ancestor of the h1 that
            // is large enough to be the "top card" — usually 3-5 levels up.
            // We grab 4 levels up and cap at 4000 chars for readability.
            let topCardHtml = null;
            if (h1) {
                let node = h1;
                for (let i = 0; i < 4 && node.parentElement; i++) node = node.parentElement;
                topCardHtml = (node.outerHTML || '').slice(0, 4000);
            }

            return {
                h1Text: h1 ? (h1.innerText || '').trim() : null,
                imgsInMain: imgs,
                pictureSources: sources,
                wildHits,
                topCardHtmlSnippet: topCardHtml,
            };
            }"""
        )

        print("\n=== H1 ===")
        print(result.get("h1Text"))

        print(f"\n=== <img> elements in <main>: {len(result['imgsInMain'])} ===")
        for i, img in enumerate(result["imgsInMain"]):
            print(f"\n[{i}] depth={img['depthToH1']} sharedAncestor={img['sharedAncestor']} cls={img['cls']!r}")
            for k in ("src", "srcset", "dataDelayedUrl", "dataLiSrc", "alt", "ariaLabel"):
                v = img.get(k)
                if v:
                    print(f"     {k}: {v[:200]}")
            print(f"     size={img['width']}x{img['height']} navBlacklisted={img['inNavBlacklist']}")

        print(f"\n=== <picture><source> elements in <main>: {len(result['pictureSources'])} ===")
        for i, src in enumerate(result["pictureSources"]):
            print(f"\n[{i}] depth={src['depthToH1']} sharedAncestor={src['sharedAncestor']}")
            for k in ("srcset", "media", "type"):
                v = src.get(k)
                if v:
                    print(f"     {k}: {v[:200]}")

        print(f"\n=== Anywhere-on-page attrs matching profile-(displayphoto|framedphoto): {len(result['wildHits'])} ===")
        for i, hit in enumerate(result["wildHits"]):
            print(f"  [{i}] <{hit['tag']} class={hit['cls']!r}> @{hit['attr']} = {hit['value']}")

        print("\n=== Top-card outerHTML (truncated 4000 chars) ===")
        print(result.get("topCardHtmlSnippet"))

        out_path = "exports/diagnose_photo_dom.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nFull JSON dumped to {out_path}")

        print("\nBrowser will stay open for 30s so you can inspect manually...")
        await page.wait_for_timeout(30000)
        await browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="LinkedIn profile URL")
    args = parser.parse_args()
    asyncio.run(diagnose(args.url))


if __name__ == "__main__":
    main()
