const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, Header, Footer, PageNumber, PageBreak,
} = require("docx");

const tb = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cb = { top: tb, bottom: tb, left: tb, right: tb };
const hdrShade = { fill: "1A1A2E", type: ShadingType.CLEAR };
const greenShade = { fill: "ECFDF5", type: ShadingType.CLEAR };
const orangeShade = { fill: "FFF7ED", type: ShadingType.CLEAR };
const grayShade = { fill: "F9FAFB", type: ShadingType.CLEAR };

function bold(t) { return new TextRun({ text: t, bold: true }); }
function normal(t) { return new TextRun({ text: t }); }
function orange(t) { return new TextRun({ text: t, bold: true, color: "E76315" }); }
function green(t) { return new TextRun({ text: t, color: "059669", bold: true }); }
function gray(t) { return new TextRun({ text: t, color: "6B7280" }); }
function code(t) { return new TextRun({ text: t, font: "Courier New", size: 18, color: "374151" }); }

function p(children, opts = {}) {
  return new Paragraph({ children: Array.isArray(children) ? children : [normal(children)], ...opts });
}
function spacer() { return p([], { spacing: { before: 40, after: 40 } }); }

function tableRow(cells, header = false) {
  return new TableRow({
    tableHeader: header,
    children: cells.map(c => new TableCell({
      borders: cb,
      width: { size: c.w, type: WidthType.DXA },
      shading: header ? hdrShade : (c.shade || undefined),
      children: [new Paragraph({
        spacing: { before: 40, after: 40 },
        children: Array.isArray(c.t) ? c.t : [new TextRun({
          text: c.t, bold: header, color: header ? "FFFFFF" : "333333",
          size: header ? 20 : 19, font: "Arial",
        })],
      })],
    })),
  });
}

const doc = new Document({
  creator: "Kanyuchi",
  title: "POT Matchmaker - Team Update | April 1, 2026",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: "1A1A2E", font: "Arial" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: "2D2D5E", font: "Arial" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "444488", font: "Arial" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "num-next", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "num-runa", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: { margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 } },
    },
    headers: {
      default: new Header({ children: [p([
        new TextRun({ text: "POT Matchmaker \u2014 Team Update", size: 16, color: "999999", italics: true }),
      ], { alignment: AlignmentType.RIGHT })] }),
    },
    footers: {
      default: new Footer({ children: [p([
        new TextRun({ text: "Confidential \u2014 XVentures Labs  |  Page ", size: 16, color: "999999" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "999999" }),
      ], { alignment: AlignmentType.CENTER })] }),
    },
    children: [
      // ── Title ──
      p([new TextRun({ text: "POT Matchmaker", size: 44, bold: true, color: "1A1A2E" })], { alignment: AlignmentType.CENTER, spacing: { after: 60 } }),
      p([new TextRun({ text: "Team Update | April 1, 2026", size: 28, color: "6B7280" })], { alignment: AlignmentType.CENTER, spacing: { after: 100 } }),
      p([new TextRun({ text: "Covering: March 30 \u2013 April 1, 2026", size: 20, color: "9CA3AF" })], { alignment: AlignmentType.CENTER, spacing: { after: 300 } }),

      // ── TL;DR ──
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("TL;DR")] }),
      p([normal("Three major integrations shipped this week: "), bold("The Grid B2B data"), normal(" (verified Web3 company intel on match cards), "), bold("Runa integration API"), normal(" (4 endpoints ready for Swerve), and "), bold("Privacy Mode"), normal(" (anonymous profiles for pseudonymous Web3 attendees). Production is live at "), orange("meet.proofoftalk.io"), normal(".")]),

      // ── Current Numbers ──
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Current Numbers")] }),
      new Table({
        columnWidths: [4680, 4680],
        rows: [
          tableRow([{ t: "Metric", w: 4680 }, { t: "Value", w: 4680 }], true),
          tableRow([{ t: "Total attendees", w: 4680 }, { t: "56", w: 4680 }]),
          tableRow([{ t: "Matches generated", w: 4680 }, { t: "144 (avg score 0.70)", w: 4680 }]),
          tableRow([{ t: "LinkedIn profiles found", w: 4680 }, { t: "30/56 (54%)", w: 4680 }]),
          tableRow([{ t: "Grid B2B data", w: 4680 }, { t: [green("15/56 (27%)")], w: 4680, shade: greenShade }]),
          tableRow([{ t: "AI summaries + embeddings", w: 4680 }, { t: "56/56 (100%)", w: 4680 }]),
          tableRow([{ t: "Vertical tags classified", w: 4680 }, { t: "56/56 (100%)", w: 4680 }]),
          tableRow([{ t: "Production URL", w: 4680 }, { t: [orange("meet.proofoftalk.io")], w: 4680 }]),
        ],
      }),

      // ── 1. The Grid Integration ──
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. The Grid B2B Data Integration")] }),
      p([bold("What:"), normal(" We integrated The Grid (thegrid.id) \u2014 the industry-standard Web3 company database with 10,000+ verified profiles. When an attendee's company is found on The Grid, their match card now shows verified B2B intelligence.")]),
      spacer(),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("What attendees see")] }),
      p("Every match card now has an expandable Grid org card:"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Compact view (always visible): "), normal("company logo, verified badge, sector, tagline, description")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Expanded view (click to open): "), normal("full description, social links (Twitter, Discord, GitHub, Telegram), products with types, legal entities with country, founded date, link to Grid profile")] }),
      spacer(),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Coverage")] }),
      new Table({
        columnWidths: [5000, 4360],
        rows: [
          tableRow([{ t: "Company", w: 5000 }, { t: "Grid Match", w: 4360 }], true),
          tableRow([{ t: "Kraken", w: 5000 }, { t: [green("Kraken (Finance)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "KuCoin", w: 5000 }, { t: [green("KuCoin (Finance)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "The Sandbox (SEBASTIEN BORGET)", w: 5000 }, { t: [green("The Sandbox (Gaming)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "Cardano Foundation", w: 5000 }, { t: [green("Cardano (Blockchain Platforms)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "SoftStack", w: 5000 }, { t: [green("SoftStack (Service Provider)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "Carbon Ratings", w: 5000 }, { t: [green("CCRI (Data & Analytics)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "Summ", w: 5000 }, { t: [green("Summ (Accounting & Legal)")], w: 4360, shade: greenShade }]),
          tableRow([{ t: "30 smaller companies", w: 5000 }, { t: [gray("Not yet in Grid database")], w: 4360, shade: grayShade }]),
        ],
      }),
      spacer(),
      p([gray("Grid coverage will improve as: (a) more Web3 companies register on The Grid, (b) we run re-enrichment after new ticket purchases. The Grid API is free and public \u2014 no ongoing cost.")]),

      // ── How it helps matching ──
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("How it improves matching")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("Grid company descriptions are now included in the AI embedding \u2014 matches based on what the company actually does, not just job title")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("Grid sector tags complement our 12 verticals \u2014 more precise cross-sector matching")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("For anonymous/pseudonymous attendees (privacy mode), Grid data is the primary visible intelligence \u2014 makes B2B-only profiles actually useful")] }),

      // ── 2. Runa Integration ──
      new Paragraph({ children: [new PageBreak()] }),
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Runa Integration API (for Swerve)")] }),
      p([bold("Goal:"), normal(" Allow Runa ticket buyers to access the matchmaker seamlessly \u2014 no separate registration. Customer buys ticket on Runa \u2192 clicks \"View My Matches\" \u2192 lands in their personal matchmaker dashboard.")]),
      spacer(),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("What we built")] }),
      p("Four API endpoints, all live and deployed:"),
      new Table({
        columnWidths: [2800, 3200, 3360],
        rows: [
          tableRow([{ t: "Endpoint", w: 2800 }, { t: "Purpose", w: 3200 }, { t: "Status", w: 3360 }], true),
          tableRow([
            { t: [code("GET /magic-link")], w: 2800 },
            { t: "Look up attendee by email, return magic link URL", w: 3200 },
            { t: [green("Live + tested")], w: 3360, shade: greenShade },
          ]),
          tableRow([
            { t: [code("POST /ticket-purchased")], w: 2800 },
            { t: "Webhook: Runa pushes ticket data on purchase", w: 3200 },
            { t: [green("Live + tested")], w: 3360, shade: greenShade },
          ]),
          tableRow([
            { t: [code("POST /ticket-cancelled")], w: 2800 },
            { t: "Webhook: deactivate on refund", w: 3200 },
            { t: [green("Live")], w: 3360, shade: greenShade },
          ]),
          tableRow([
            { t: [code("GET /attendee-status")], w: 2800 },
            { t: "Check match count, profile status", w: 3200 },
            { t: [green("Live")], w: 3360, shade: greenShade },
          ]),
        ],
      }),
      spacer(),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("How it works (minimum integration)")] }),
      new Paragraph({ numbering: { reference: "num-runa", level: 0 }, children: [normal("Customer clicks \"View My Matches\" in Runa")] }),
      new Paragraph({ numbering: { reference: "num-runa", level: 0 }, children: [normal("Runa calls our API with the customer's email \u2192 gets back a magic link URL")] }),
      new Paragraph({ numbering: { reference: "num-runa", level: 0 }, children: [normal("Runa redirects the customer to that URL")] }),
      new Paragraph({ numbering: { reference: "num-runa", level: 0 }, children: [normal("Customer lands in their personal matchmaker dashboard (no login needed)")] }),
      spacer(),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("What Swerve needs to do")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Review the spec doc "), normal("(attached: runa-integration-spec.docx) \u2014 covers all endpoints, schemas, and open questions")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Fix the DNS record "), normal("\u2014 meet.proofoftalk.io CNAME was missing, "), green("now restored")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Add a \"View My Matches\" button "), normal("in Runa's post-purchase flow or ticket dashboard")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Answer open questions "), normal("(section 7 in spec): webhook vs pull, ticket type mapping, iframe vs redirect")] }),
      spacer(),
      p([gray("Staging URL for Swerve: http://3.239.218.239/api/v1/integration/")]),
      p([gray("Production URL: https://meet.proofoftalk.io/api/v1/integration/")]),

      // ── 3. Privacy Mode ──
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Privacy Mode (Anonymous Profiles)")] }),
      p([bold("Context:"), normal(" Jes raised that many Web3 ambassadors are pseudonymous \u2014 they don't use real names/photos publicly. When they claim a ticket, their identity gets exposed on match cards.")]),
      spacer(),
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("What we built")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Privacy toggle on Profile page "), normal("\u2014 attendees can switch between \"Full profile\" and \"B2B Only\"")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("B2B Only mode hides: "), normal("name, photo, title, LinkedIn, Twitter, email, AI summary")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("B2B Only mode shows: "), normal("company name, verticals, intent tags, Grid data, deal readiness, interests, goals")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Reveal on mutual match: "), normal("once both parties accept the match, personal info is automatically revealed to each other")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Match cards show \"B2B Profile\" badge "), normal("so the other person knows it's an anonymous profile")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Emails respect privacy: "), normal("match intros use company name for anonymous attendees; mutual match emails reveal real names (both consented)")] }),

      // ── 4. Other Improvements ──
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Other Improvements This Week")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Vertical tags aligned with 1000 Minds "), normal("\u2014 12 verticals (added Privacy), display names, purple-styled tags visible on all match cards")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Directory cleanup "), normal("\u2014 removed temp files, reorganised docs/scripts, consolidated dependencies")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("DNS restored "), normal("\u2014 meet.proofoftalk.io CNAME re-added, production URL fully operational")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("UX fix "), normal("\u2014 non-admin attendees no longer see \"Admin access required\" \u2014 silently redirected to their matches")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Enrichment data quality "), normal("\u2014 improved Grid company name matching (smart normalization for Extasy-derived names), batch re-enrichment run")] }),

      // ── 5. Next Steps ──
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Next Steps")] }),
      new Table({
        columnWidths: [800, 4200, 4360],
        rows: [
          tableRow([{ t: "#", w: 800 }, { t: "Task", w: 4200 }, { t: "Owner / Status", w: 4360 }], true),
          tableRow([{ t: "1", w: 800 }, { t: "Share Runa spec + API key with Swerve", w: 4200 }, { t: [orange("Kanyuchi \u2014 this week")], w: 4360, shade: orangeShade }]),
          tableRow([{ t: "2", w: 800 }, { t: "Swerve: review spec, add \"View Matches\" button in Runa", w: 4200 }, { t: "Swerve \u2014 pending", w: 4360 }]),
          tableRow([{ t: "3", w: 800 }, { t: "Scale test to 50+ real profiles (Chiara data)", w: 4200 }, { t: "Blocked on Chiara", w: 4360 }]),
          tableRow([{ t: "4", w: 800 }, { t: "Email provider switch (SES denied, need Resend/SendGrid)", w: 4200 }, { t: "Needs Victor + DNS", w: 4360 }]),
          tableRow([{ t: "5", w: 800 }, { t: "Full end-to-end journey test (match \u2192 mutual \u2192 meet)", w: 4200 }, { t: "Kanyuchi \u2014 soon", w: 4360 }]),
          tableRow([{ t: "6", w: 800 }, { t: "Re-enrichment batch after new ticket sync", w: 4200 }, { t: "Automated (daily 02:00 UTC)", w: 4360 }]),
        ],
      }),
      spacer(),
      spacer(),
      p([bold("Questions or feedback? "), normal("Reach out to Kanyuchi.")], { alignment: AlignmentType.CENTER }),
    ],
  }],
});

const outPath = "/Users/fadzie/Desktop/Proof_Of_Talk_CD/docs/team-update-2026-04-01.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("Created:", outPath);
});
