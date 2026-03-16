const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, LevelFormat, UnderlineType,
  PageBreak,
} = require("docx");

// ── Colours ───────────────────────────────────────────────────────────────────
const AMBER   = "D97706";   // warm amber for section headers
const DARK    = "111827";   // near-black for headings
const SLATE   = "1E293B";   // dark slate
const MID     = "374151";   // mid-gray body
const LIGHT   = "6B7280";   // light gray for captions
const RED     = "DC2626";   // missing fields
const GREEN   = "059669";   // available fields
const ORANGE  = "D97706";   // partial fields
const BG_DARK = "1E293B";   // header cell background
const BG_MID  = "F3F4F6";   // alt row (light mode for Word readability)
const BG_AMB  = "FEF3C7";   // amber-tinted row
const WHITE   = "FFFFFF";

// ── Borders ───────────────────────────────────────────────────────────────────
const thinBorder  = { style: BorderStyle.SINGLE, size: 4, color: "D1D5DB" };
const cellBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };
const noBorder    = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noCellBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// ── Total usable width: A4 with 2.5cm margins = ~8686 DXA ────────────────────
const W = 8686;

// ── Helpers ───────────────────────────────────────────────────────────────────
const sp = (before = 0, after = 0) => ({ spacing: { before, after } });

function hCell(text, w, bg = BG_DARK) {
  return new TableCell({
    borders: cellBorders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: bg, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      ...sp(60, 60),
      children: [new TextRun({ text, bold: true, color: WHITE, size: 18, font: "Arial" })],
    })],
  });
}

function dCell(children, w, bg = WHITE) {
  return new TableCell({
    borders: cellBorders,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: bg, type: ShadingType.CLEAR },
    verticalAlign: VerticalAlign.TOP,
    children: Array.isArray(children) ? children : [children],
  });
}

function bodyP(text, opts = {}) {
  return new Paragraph({
    ...sp(40, 40),
    children: [new TextRun({ text, size: 20, font: "Arial", color: MID, ...opts })],
  });
}

function bulletP(text, ref = "bullet-list") {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    ...sp(30, 30),
    children: [new TextRun({ text, size: 20, font: "Arial", color: MID })],
  });
}

function sectionHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    ...sp(280, 100),
    children: [new TextRun({ text, bold: true, color: AMBER, size: 28, font: "Arial" })],
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: AMBER } },
  });
}

function subHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    ...sp(200, 80),
    children: [new TextRun({ text, bold: true, color: DARK, size: 22, font: "Arial" })],
  });
}

function statusRun(text, color) {
  return new TextRun({ text, bold: true, color, size: 19, font: "Arial" });
}

// ── Document ──────────────────────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 20, color: MID } } },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
        run: { size: 28, bold: true, color: AMBER, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 0 },
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
        run: { size: 22, bold: true, color: DARK, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1 },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullet-list",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u2022",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 260 } } },
        }],
      },
      {
        reference: "step-list",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 300 } } },
        }],
      },
      {
        reference: "indent-bullet",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "\u2013",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 900, hanging: 260 } } },
        }],
      },
    ],
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1260, bottom: 1440, left: 1260 } },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "E5E7EB" } },
          ...sp(0, 60),
          children: [
            new TextRun({ text: "POT Matchmaker  |  ", color: LIGHT, size: 16, font: "Arial" }),
            new TextRun({ text: "Data Completeness Gap Analysis", color: AMBER, size: 16, font: "Arial", bold: true }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "E5E7EB" } },
          ...sp(60, 0),
          children: [
            new TextRun({ text: "Proof of Talk 2026  \u00B7  Kanyuchi  \u00B7  Page ", color: LIGHT, size: 16, font: "Arial" }),
            new TextRun({ children: [PageNumber.CURRENT], color: LIGHT, size: 16, font: "Arial" }),
            new TextRun({ text: " of ", color: LIGHT, size: 16, font: "Arial" }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], color: LIGHT, size: 16, font: "Arial" }),
          ],
        })],
      }),
    },

    children: [

      // ── COVER ──────────────────────────────────────────────────────────────
      // Title block
      new Table({
        columnWidths: [W],
        margins: { top: 0, bottom: 0, left: 0, right: 0 },
        rows: [
          new TableRow({ children: [
            new TableCell({
              borders: noCellBorders,
              width: { size: W, type: WidthType.DXA },
              shading: { fill: SLATE, type: ShadingType.CLEAR },
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  ...sp(160, 40),
                  children: [new TextRun({ text: "DATA COMPLETENESS GAP ANALYSIS", bold: true, color: AMBER, size: 26, font: "Arial", allCaps: true })],
                }),
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  ...sp(40, 40),
                  children: [new TextRun({ text: "Extasy API  vs  Matching Engine Requirements", bold: true, color: WHITE, size: 44, font: "Arial" })],
                }),
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  ...sp(40, 160),
                  children: [new TextRun({ text: "POT Matchmaker  \u00B7  XVentures Labs  \u00B7  Proof of Talk 2026", color: "9CA3AF", size: 18, font: "Arial" })],
                }),
              ],
            }),
          ]}),
        ],
      }),

      new Paragraph({ ...sp(60, 0), children: [] }),

      // Meta row
      new Table({
        columnWidths: [Math.floor(W/3), Math.floor(W/3), W - 2*Math.floor(W/3)],
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        rows: [new TableRow({ children: [
          new TableCell({
            borders: noCellBorders,
            width: { size: Math.floor(W/3), type: WidthType.DXA },
            shading: { fill: "F9FAFB", type: ShadingType.CLEAR },
            children: [
              new Paragraph({ children: [new TextRun({ text: "PROJECT", color: LIGHT, size: 14, font: "Arial", allCaps: true, bold: true })], ...sp(0,20) }),
              new Paragraph({ children: [new TextRun({ text: "POT Matchmaker", color: DARK, size: 20, font: "Arial", bold: true })] }),
            ],
          }),
          new TableCell({
            borders: noCellBorders,
            width: { size: Math.floor(W/3), type: WidthType.DXA },
            shading: { fill: "F9FAFB", type: ShadingType.CLEAR },
            children: [
              new Paragraph({ children: [new TextRun({ text: "AUTHOR", color: LIGHT, size: 14, font: "Arial", allCaps: true, bold: true })], ...sp(0,20) }),
              new Paragraph({ children: [new TextRun({ text: "Kanyuchi", color: DARK, size: 20, font: "Arial", bold: true })] }),
            ],
          }),
          new TableCell({
            borders: noCellBorders,
            width: { size: W - 2*Math.floor(W/3), type: WidthType.DXA },
            shading: { fill: "F9FAFB", type: ShadingType.CLEAR },
            children: [
              new Paragraph({ children: [new TextRun({ text: "DATE", color: LIGHT, size: 14, font: "Arial", allCaps: true, bold: true })], ...sp(0,20) }),
              new Paragraph({ children: [new TextRun({ text: "March 2026", color: DARK, size: 20, font: "Arial", bold: true })] }),
            ],
          }),
        ]})],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 1. CONTEXT ─────────────────────────────────────────────────────────
      sectionHeading("1. Context"),
      new Paragraph({
        ...sp(60, 80),
        children: [
          new TextRun({ text: "We have ", size: 20, font: "Arial", color: MID }),
          new TextRun({ text: "15 confirmed PAID attendees", bold: true, size: 20, font: "Arial", color: DARK }),
          new TextRun({ text: " from the Extasy ticketing API. The question is whether this data is sufficient to power the POT Matchmaker AI engine. The answer is: ", size: 20, font: "Arial", color: MID }),
          new TextRun({ text: "it covers identity only — approximately 15% of what the engine actually needs.", bold: true, size: 20, font: "Arial", color: DARK }),
          new TextRun({ text: " This document maps the gaps and defines a 3-layer strategy to close them before the event.", size: 20, font: "Arial", color: MID }),
        ],
      }),

      // Stat cards (table)
      new Table({
        columnWidths: [Math.floor(W/4), Math.floor(W/4), Math.floor(W/4), W - 3*Math.floor(W/4)],
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        rows: [new TableRow({ children: [
          ...[
            ["15", "Confirmed\nPAID attendees", AMBER],
            ["~15%", "Data coverage\nfrom Extasy alone", RED],
            ["3 layers", "Gap closure\nstrategy", GREEN],
            ["June 2\u20133", "Louvre Palace\nParis", "4B5563"],
          ].map(([num, label, color], i) => new TableCell({
            borders: { top: { style: BorderStyle.SINGLE, size: 12, color }, bottom: thinBorder, left: thinBorder, right: thinBorder },
            width: { size: i < 3 ? Math.floor(W/4) : W - 3*Math.floor(W/4), type: WidthType.DXA },
            shading: { fill: "F9FAFB", type: ShadingType.CLEAR },
            children: [
              new Paragraph({ alignment: AlignmentType.CENTER, ...sp(80, 20), children: [new TextRun({ text: num, bold: true, size: 40, color, font: "Arial" })] }),
              new Paragraph({ alignment: AlignmentType.CENTER, ...sp(0, 80), children: [new TextRun({ text: label.replace("\n", "  "), size: 16, color: LIGHT, font: "Arial" })] }),
            ],
          })),
        ]})],
      }),

      new Paragraph({ ...sp(120, 0), children: [] }),

      // ── 2. WHAT EXTASY PROVIDES ────────────────────────────────────────────
      sectionHeading("2. What Extasy Provides (Per Attendee)"),
      bodyP("The table below shows every field available from the Extasy ticketing API and its quality for matching purposes."),
      new Paragraph({ ...sp(80, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.22), Math.floor(W*0.14), Math.floor(W*0.12), W - Math.floor(W*0.22) - Math.floor(W*0.14) - Math.floor(W*0.12)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [
            hCell("Field", Math.floor(W*0.22)),
            hCell("Available", Math.floor(W*0.14)),
            hCell("Quality", Math.floor(W*0.12)),
            hCell("Notes", W - Math.floor(W*0.22) - Math.floor(W*0.14) - Math.floor(W*0.12)),
          ]}),
          ...[
            ["name",                   "✓ Yes",     GREEN,  "Good",   "First + last from registration"],
            ["email",                  "✓ Yes",     GREEN,  "Good",   "Enables all downstream enrichment"],
            ["phone_number",           "✓ Yes",     GREEN,  "Good",   "Useful for direct contact"],
            ["ticket_type",            "✓ Yes",     GREEN,  "Good",   "Maps to vip / delegate / speaker / sponsor"],
            ["city / country",         "✓ Yes",     GREEN,  "Good",   "ISO3 country code + city name"],
            ["bought_date",            "✓ Yes",     GREEN,  "Good",   "Useful for prioritisation"],
            ["company",                "⚠ Partial", ORANGE, "Weak",   "Inferred from email domain only (e.g. @kraken.com → Kraken)"],
            ["title",                  "✗ No",      RED,    "—",      "Not in API — must be enriched or self-reported"],
            ["interests",              "✗ No",      RED,    "—",      "Not in API — core input to embedding"],
            ["goals",                  "✗ No",      RED,    "—",      "Not in API — highest signal field for matching"],
            ["seeking / not_looking",  "✗ No",      RED,    "—",      "Not in API — used for hard filter in Stage 2"],
            ["preferred_geographies",  "✗ No",      RED,    "—",      "Not in API — optional hard filter"],
            ["deal_stage",             "✗ No",      RED,    "—",      "Not in API — critical for deal-ready matching"],
            ["linkedin_url",           "✗ No",      RED,    "—",      "Not in API — unlocks LinkedIn enrichment via Proxycurl"],
            ["twitter_handle",         "✗ No",      RED,    "—",      "Not in API — unlocks real-time activity enrichment"],
          ].map(([field, avail, color, quality, notes], i) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: field, size: 18, font: "Courier New", color: DARK, bold: true })] }), Math.floor(W*0.22), i % 2 === 0 ? WHITE : "F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [statusRun(avail, color)] }), Math.floor(W*0.14), i % 2 === 0 ? WHITE : "F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: quality, size: 18, font: "Arial", color: LIGHT })] }), Math.floor(W*0.12), i % 2 === 0 ? WHITE : "F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: notes, size: 18, font: "Arial", color: MID })] }), W - Math.floor(W*0.22) - Math.floor(W*0.14) - Math.floor(W*0.12), i % 2 === 0 ? WHITE : "F9FAFB"),
            ]})
          ),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 3. WHAT THE MATCHING ENGINE NEEDS ─────────────────────────────────
      sectionHeading("3. What the Matching Engine Actually Needs"),

      subHeading("3.1 Hard Requirements"),
      bodyP("The engine cannot generate quality matches without all four of the following:"),
      new Paragraph({ ...sp(60, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.22), W - Math.floor(W*0.22)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [hCell("Field", Math.floor(W*0.22)), hCell("Purpose", W - Math.floor(W*0.22))] }),
          ...([
            ["embedding",   "1536-dim vector — generated from composite profile text via OpenAI text-embedding-3-small"],
            ["ai_summary",  "GPT-4o generated — 2–3 sentence professional summary, key input to composite text"],
            ["intent_tags", "GPT-4o classified — used as hard filter in Stage 2 candidate retrieval"],
            ["ticket_type", "Used for eligibility filtering — Extasy provides this ✓"],
          ].map(([f, p], i) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: f, bold: true, size: 18, font: "Courier New", color: DARK })] }), Math.floor(W*0.22), i === 3 ? "ECFDF5" : (i%2===0?WHITE:"F9FAFB")),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: p, size: 18, font: "Arial", color: MID })] }), W - Math.floor(W*0.22), i === 3 ? "ECFDF5" : (i%2===0?WHITE:"F9FAFB")),
            ]})
          )),
        ],
      }),

      new Paragraph({ ...sp(120, 0), children: [] }),
      subHeading("3.2 Composite Text Inputs (fed to OpenAI for embedding)"),
      bodyP("The richer these fields are, the better the match quality. They are concatenated into a single text blob and embedded as a 1536-dim vector:"),
      new Paragraph({ ...sp(60, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.28), W - Math.floor(W*0.28)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [hCell("Composite field", Math.floor(W*0.28)), hCell("Source & gap", W - Math.floor(W*0.28))] }),
          ...([
            ["name, title, company",   "Extasy has name only — title and company are absent or inferred"],
            ["interests, goals",       "Completely absent from Extasy — highest signal inputs for matching"],
            ["ai_summary",             "Generated by GPT-4o after other fields are populated"],
            ["linkedin_summary",       "From Proxycurl enrichment — requires PROXYCURL_API_KEY"],
            ["company_description",    "From website scraping — no API key needed, uses email domain as URL"],
            ["recent_activity",        "From Twitter/X enrichment — requires TWITTER_BEARER_TOKEN"],
            ["funding_info",           "From Crunchbase scraping — no API key needed for basic data"],
          ].map(([f, s], i) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: f, bold: true, size: 18, font: "Courier New", color: DARK })] }), Math.floor(W*0.28), i%2===0?WHITE:"F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: s, size: 18, font: "Arial", color: MID })] }), W - Math.floor(W*0.28), i%2===0?WHITE:"F9FAFB"),
            ]})
          )),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 4. GAP CLOSURE STRATEGY ────────────────────────────────────────────
      sectionHeading("4. Gap Closure Strategy — 3-Layer Approach"),

      // Layer 1
      subHeading("Layer 1 — Email-Domain Enrichment (immediate, no API keys needed)"),
      bulletP("Infer company name and website URL from email domain. Already implemented in the ingest script."),
      bulletP("Examples from current 15 confirmed attendees:"),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "kaushik.sthankiya@kraken.com → Kraken (crypto exchange) · https://kraken.com", size: 18, font: "Arial", color: MID })] }),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "nmehta@clearstreet.io → Clear Street (prime brokerage) · https://clearstreet.io", size: 18, font: "Arial", color: MID })] }),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "robin.s@kucoin.com → KuCoin (crypto exchange) · https://kucoin.com", size: 18, font: "Arial", color: MID })] }),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "laurence@theqrl.org → QRL (quantum-resistant blockchain) · https://theqrl.org", size: 18, font: "Arial", color: MID })] }),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,80), children: [new TextRun({ text: "dariia.p@eternax.ai → Eternax (AI/Web3) · https://eternax.ai", size: 18, font: "Arial", color: MID })] }),
      bulletP("Outcome: company_website field populated → enables Layer 2 website scraping."),

      new Paragraph({ ...sp(100, 0), children: [] }),

      // Layer 2
      subHeading("Layer 2 — Enrichment Pipeline (runs post-ingestion)"),
      bulletP("Company website scraping (no API key needed) — uses httpx + BeautifulSoup:"),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "Extracts: company description, sector, product positioning from meta tags and body text.", size: 18, font: "Arial", color: MID })] }),
      bulletP("LinkedIn via Proxycurl (requires PROXYCURL_API_KEY):"),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "Extracts: title, career history, headline, skills, linkedin_summary.", size: 18, font: "Arial", color: MID })] }),
      bulletP("Twitter/X API (requires TWITTER_BEARER_TOKEN):"),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,20), children: [new TextRun({ text: "Extracts: recent_activity, positioning, informal interests.", size: 18, font: "Arial", color: MID })] }),
      bulletP("Crunchbase scraping (no API key needed for basic data):"),
      new Paragraph({ numbering: { reference: "indent-bullet", level: 0 }, ...sp(20,40), children: [new TextRun({ text: "Extracts: funding rounds, total raised, investor names, sector categories.", size: 18, font: "Arial", color: MID })] }),
      new Paragraph({ ...sp(40,0), children: [new TextRun({ text: "Run command: ", size: 18, font: "Arial", color: LIGHT }), new TextRun({ text: "python scripts/enrich_and_embed.py", bold: true, size: 18, font: "Courier New", color: DARK })] }),

      new Paragraph({ ...sp(100, 0), children: [] }),

      // Layer 3
      subHeading("Layer 3 — Attendee Onboarding Form (highest signal — now built)"),
      bodyP("A lightweight post-purchase form sent to confirmed attendees at /onboarding. This is the strategy used by Brella and other tier-1 event matchmakers. Without this layer, the engine falls back entirely on enrichment inference."),
      new Paragraph({ ...sp(60, 0), children: [] }),
      bulletP("title + company (confirm or correct the inferred values)"),
      bulletP("goals — 'What do you want to achieve at POT 2026?'"),
      bulletP("interests — select from a curated taxonomy (15 topics)"),
      bulletP("deal_stage — are you raising, deploying, building?"),
      bulletP("seeking — who do you want to meet?"),
      bulletP("linkedin_url (optional — triggers Proxycurl enrichment)"),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 5. MATCH QUALITY MATRIX ────────────────────────────────────────────
      sectionHeading("5. Expected Match Quality by Data Layer"),
      bodyP("The table below shows expected match quality at each enrichment stage:"),
      new Paragraph({ ...sp(80, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.22), Math.floor(W*0.28), Math.floor(W*0.25), W - Math.floor(W*0.22) - Math.floor(W*0.28) - Math.floor(W*0.25)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [
            hCell("Data State", Math.floor(W*0.22)),
            hCell("Composite Text Quality", Math.floor(W*0.28)),
            hCell("Match Quality", Math.floor(W*0.25)),
            hCell("Verdict", W - Math.floor(W*0.22) - Math.floor(W*0.28) - Math.floor(W*0.25)),
          ]}),
          ...([
            ["Extasy only (no enrichment)", "Name: X, Ticket Type: vip — almost nothing", "Very low — essentially random within tier", "✗ Not viable", RED, WHITE],
            ["+ Website scraping (no API keys)", "Adds company description, sector, rough positioning", "Sector-level accurate but not deal-ready", "⚠ Functional but shallow", ORANGE, "FFFBEB"],
            ["+ LinkedIn enrichment (Proxycurl)", "Adds title, career history, professional positioning", "Good — intent tags become meaningful", "✓ Production ready", GREEN, "ECFDF5"],
            ["+ Onboarding form (all layers)", "Full composite profile — equivalent to seed profiles", "Best — matches on par with the demo", "✓✓ Optimal", AMBER, "FFFBEB"],
          ].map(([state, comp, quality, verdict, color, bg]) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: state, bold: true, size: 18, font: "Arial", color: DARK })] }), Math.floor(W*0.22), bg),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: comp, size: 18, font: "Arial", color: MID })] }), Math.floor(W*0.28), bg),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: quality, size: 18, font: "Arial", color: MID })] }), Math.floor(W*0.25), bg),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: verdict, bold: true, size: 18, font: "Arial", color })] }), W - Math.floor(W*0.22) - Math.floor(W*0.28) - Math.floor(W*0.25), bg),
            ]})
          )),
        ],
      }),

      new Paragraph({ ...sp(120, 0), children: [] }),

      // ── 6. IMPLEMENTATION PLAN ─────────────────────────────────────────────
      sectionHeading("6. Recommended Implementation Plan"),
      new Paragraph({ ...sp(60, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.07), Math.floor(W*0.35), Math.floor(W*0.40), W - Math.floor(W*0.07) - Math.floor(W*0.35) - Math.floor(W*0.40)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [
            hCell("#", Math.floor(W*0.07)),
            hCell("Step", Math.floor(W*0.35)),
            hCell("Detail", Math.floor(W*0.40)),
            hCell("Status", W - Math.floor(W*0.07) - Math.floor(W*0.35) - Math.floor(W*0.40)),
          ]}),
          ...([
            ["1", "Run schema migration in Supabase", "File: backend/scripts/supabase_setup.sql\nRun once in Supabase SQL editor", "Blocked on DB credentials", ORANGE],
            ["2", "Run Extasy ingestion", "python scripts/ingest_extasy.py\nResult: 15 attendees in Supabase with identity + company_website fields", "Ready", GREEN],
            ["3", "Run website scraping enrichment", "python scripts/enrich_and_embed.py --scrape-only\nResult: company_description added to enriched_profile", "Ready (no API key needed)", GREEN],
            ["4", "Run AI summary + intent + embedding", "python scripts/enrich_and_embed.py\nResult: ai_summary, intent_tags, embedding, deal_readiness_score populated", "Needs OPENAI_API_KEY", ORANGE],
            ["5", "Generate matches", "POST /api/matches/generate-all via admin dashboard\nResult: match pairs with scores + GPT-4o explanations", "Ready after Step 4", ORANGE],
            ["6", "Proxycurl LinkedIn enrichment (optional)", "Set PROXYCURL_API_KEY in .env, re-run enrich_and_embed.py --force\nResult: title, career history, linkedin_summary added", "Optional — API key needed", LIGHT],
            ["7", "Attendee onboarding form (live)", "Send /onboarding link to all 15 confirmed attendees\nAuth: Extasy ticket code from confirmation email\nCollects: title, company, goals, interests, deal_stage, seeking, linkedin_url", "Live — highest priority", GREEN],
          ].map(([num, step, detail, status, color], i) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), alignment: AlignmentType.CENTER, children: [new TextRun({ text: num, bold: true, size: 20, font: "Arial", color })] }), Math.floor(W*0.07), i%2===0?WHITE:"F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: step, bold: true, size: 18, font: "Arial", color: DARK })] }), Math.floor(W*0.35), i%2===0?WHITE:"F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: detail, size: 17, font: "Arial", color: MID })] }), Math.floor(W*0.40), i%2===0?WHITE:"F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: status, bold: true, size: 17, font: "Arial", color })] }), W - Math.floor(W*0.07) - Math.floor(W*0.35) - Math.floor(W*0.40), i%2===0?WHITE:"F9FAFB"),
            ]})
          )),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 7. CRITICAL FILES ──────────────────────────────────────────────────
      sectionHeading("7. Critical Files"),
      new Paragraph({ ...sp(60, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.46), W - Math.floor(W*0.46)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [hCell("File", Math.floor(W*0.46)), hCell("Purpose", W - Math.floor(W*0.46))] }),
          ...([
            ["backend/app/services/matching.py",    "3-stage matching pipeline (Embed → Retrieve → Rank & Explain)"],
            ["backend/app/services/enrichment.py",  "Multi-source enrichment (LinkedIn, Twitter, website scraping, Crunchbase)"],
            ["backend/app/services/embeddings.py",  "Composite text builder + OpenAI embedding + AI summary + intent classifier"],
            ["backend/app/models/attendee.py",       "Full field definitions for Attendee and Match SQLAlchemy models"],
            ["backend/data/seed_profiles.json",      "Reference for what a complete profile looks like (5 demo attendees)"],
            ["backend/scripts/ingest_extasy.py",     "Extasy API → Supabase ingestion script (sets company_website from email domain)"],
            ["backend/scripts/enrich_and_embed.py",  "Standalone batch enrichment + embedding script (no FastAPI server needed)"],
            ["backend/scripts/supabase_setup.sql",   "Schema migration — run once in Supabase SQL editor"],
            ["frontend/src/pages/Onboarding.tsx",    "3-step post-purchase attendee onboarding form (/onboarding route)"],
          ].map(([file, purpose], i) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: file, size: 17, font: "Courier New", color: DARK, bold: true })] }), Math.floor(W*0.46), i%2===0?WHITE:"F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: purpose, size: 18, font: "Arial", color: MID })] }), W - Math.floor(W*0.46), i%2===0?WHITE:"F9FAFB"),
            ]})
          )),
        ],
      }),

      new Paragraph({ ...sp(120, 0), children: [] }),

      // ── 8. VERIFICATION ────────────────────────────────────────────────────
      sectionHeading("8. Verification Checklist"),
      bodyP("After Steps 2–5 are complete, confirm via these API calls:"),
      new Paragraph({ ...sp(80, 0), children: [] }),

      new Table({
        columnWidths: [Math.floor(W*0.38), W - Math.floor(W*0.38)],
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        rows: [
          new TableRow({ tableHeader: true, children: [hCell("Endpoint", Math.floor(W*0.38)), hCell("Expected result", W - Math.floor(W*0.38))] }),
          ...([
            ["GET /api/attendees",             "Returns 15 real attendees from Supabase (not seed data)"],
            ["GET /api/attendees/{id}",         "enriched_profile.company_description is populated for most attendees"],
            ["GET /api/attendees/{id}",         "ai_summary, intent_tags, deal_readiness_score are non-null"],
            ["GET /api/matches/{attendee_id}",  "Match pairs returned with GPT-4o explanations and overall_score > 0.60"],
            ["GET /api/dashboard/stats",        "Dashboard shows real attendee counts and enrichment coverage %"],
          ].map(([endpoint, result], i) =>
            new TableRow({ children: [
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: endpoint, size: 17, font: "Courier New", color: DARK, bold: true })] }), Math.floor(W*0.38), i%2===0?WHITE:"F9FAFB"),
              dCell(new Paragraph({ ...sp(50,50), children: [new TextRun({ text: result, size: 18, font: "Arial", color: MID })] }), W - Math.floor(W*0.38), i%2===0?WHITE:"F9FAFB"),
            ]})
          )),
        ],
      }),

      new Paragraph({ ...sp(200, 0), children: [] }),

      // ── CLOSING LINE ───────────────────────────────────────────────────────
      new Paragraph({
        alignment: AlignmentType.CENTER,
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "E5E7EB" } },
        ...sp(120, 0),
        children: [
          new TextRun({ text: "POT Matchmaker  \u00B7  XVentures Labs Internal Entrepreneur  \u00B7  Level 3 Submission  \u00B7  Proof of Talk 2026", color: LIGHT, size: 16, font: "Arial" }),
        ],
      }),

    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/Users/fadzie/Desktop/Proof_Of_Talk_CD/docs/POT_Gap_Analysis.docx", buf);
  console.log("DOCX generated: docs/POT_Gap_Analysis.docx");
});
