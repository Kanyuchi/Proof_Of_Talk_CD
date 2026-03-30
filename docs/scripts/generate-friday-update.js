const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType, LevelFormat, Footer, PageNumber, ExternalHyperlink } = require("docx");

const orange = "E76315";
const dark = "1A1A2E";
const gray = "666666";
const lightGray = "F5F5F5";
const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "DDDDDD" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

function headerCell(text, width) {
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: dark, type: ShadingType.CLEAR },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, bold: true, color: "FFFFFF", size: 20, font: "Arial" })] })],
  });
}

function dataCell(text, width, opts = {}) {
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({ alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT, children: [new TextRun({ text, size: 20, font: "Arial", bold: !!opts.bold, color: opts.color || "333333" })] })],
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: dark, font: "Arial" }, paragraph: { spacing: { before: 360, after: 180 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, color: orange, font: "Arial" }, paragraph: { spacing: { before: 280, after: 120 } } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "feedback", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "focus", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "wins", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "POT Matchmaker \u00B7 Weekly Update \u00B7 Page ", size: 16, color: gray, font: "Arial" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: gray, font: "Arial" }),
      ] })] }),
    },
    children: [
      // Title bar
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "PROOF OF TALK 2026", size: 18, color: orange, bold: true, font: "Arial" })] }),
      new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "POT Matchmaker \u2014 Weekly Update", size: 36, bold: true, color: dark, font: "Arial" })] }),
      new Paragraph({ spacing: { after: 300 }, children: [new TextRun({ text: "Week of March 24\u201328, 2026  \u00B7  Prepared by Kanyuchi", size: 20, color: gray, font: "Arial" })] }),

      // Greeting
      new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "Hey everyone,", size: 22, font: "Arial" })] }),
      new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "Sending you my weekly overview below:", size: 22, font: "Arial" })] }),

      // Key results
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Key Results")] }),
      ...["All 5 brainstorm Quick Wins shipped (Intent Matching, QR Code, Directory, Investor Heatmap, Warm-Up Threads)",
        'Magic link access live \u2014 attendees see matches with 1 click, no login',
        '"Who do you want to meet?" field implemented \u2014 Z\'s product direction wired into matching',
        "Architecture doc + cost analysis delivered (\u20AC0.39/attendee at 2,500 scale)",
      ].map(t => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      // Progress on last week
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Progress on Last Week\u2019s Priorities")] }),
      ...[
        ["Magic link (no-login access)", "done"],
        ["Architecture/scale documentation", "done"],
        ["Cost analysis", "done"],
        ["Scale test to 50 profiles", "pending"],
        ["SES production access", "blocked"],
      ].map(([item, status]) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: item + " \u2014 ", size: 21, font: "Arial" }),
        new TextRun({ text: status, size: 21, font: "Arial", bold: true, color: status === "done" ? "10B981" : status === "blocked" ? "EF4444" : orange }),
      ] })),

      // ━━━ separator
      new Paragraph({ spacing: { before: 300, after: 300 }, children: [new TextRun({ text: "\u2501".repeat(60), color: "DDDDDD", size: 16, font: "Arial" })] }),

      // What shipped
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("What Shipped This Week")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Magic Link & Email")] }),
      ...["Magic link access: every attendee gets a unique /m/:token URL \u2014 1-click read-only match dashboard, no login required",
        "QR code in email: match intro emails include scannable QR code (CID attachment) linking to magic link",
        'Email copy updated: "Our Matchmaker has matched you" (was "The AI has matched you")',
        "SES verification emails sent to mona, nupur, hamid, victor, z",
      ].map(t => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Brainstorm Quick Wins (All 5 Shipped)")] }),
      ...["Investor Heatmap: capital activity by sector on dashboard \u2014 who\u2019s deploying capital, deal-making",
        "QR Business Card: scannable QR on Profile page linking to magic link; copy + save as PNG",
        "Pre-Event Warm-Up Threads: 11 sector-based discussion threads with live polling",
      ].map(t => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Z\u2019s Product Direction (Implemented)")] }),
      ...['"Who do you want to meet?": new target_companies field on Profile + magic link enrichment card',
        "Magic link profile enrichment: update Twitter + targets without logging in",
        "Matching integration: target_companies fed into embeddings + GPT-4o with highest priority",
      ].map(t => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("UX Polish")] }),
      ...["Auth-aware home page: logged-in users see relevant CTAs",
        "Feature card copy rewrite: removed technical jargon, now attendee-facing",
        "Social links on match cards: LinkedIn, Twitter, website icons",
        "Twitter URL fix: handles full URLs (x.com/handle) not just @handle",
        "Mutual match nav badge: orange count when someone accepted you",
        "ML feedback loop: GPT-4o receives prior decline reasons as negative examples",
        "Match card feedback: thumbs up/down for lightweight quality signals",
      ].map(t => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      // By the numbers
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("By the Numbers")] }),
      new Table({
        columnWidths: [3200, 2000, 2000, 2160],
        rows: [
          new TableRow({ children: [headerCell("Metric", 3200), headerCell("Last Week", 2000), headerCell("This Week", 2000), headerCell("Change", 2160)] }),
          ...[ ["Attendees", "38", "41", "+3"],
            ["Matches", "129", "140", "+11"],
            ["Enrichment Coverage", "100%", "100%", "\u2014"],
            ["Avg Match Score", "0.69", "0.70", "+0.01"],
            ["Matches Above 0.75", "\u2014", "36", "tracked"],
            ["Brainstorm Quick Wins", "2/5", "5/5", "+3"],
            ["OKR Definition of Done", "4/6", "5/6", "+1"],
          ].map((row, i) => new TableRow({ children: [
            dataCell(row[0], 3200, { bold: true }),
            dataCell(row[1], 2000, { center: true }),
            dataCell(row[2], 2000, { center: true, bold: true }),
            dataCell(row[3], 2160, { center: true, color: row[3].startsWith("+") ? "10B981" : gray }),
          ] })),
        ],
      }),

      new Paragraph({ spacing: { before: 300 }, children: [] }),

      // OKR Scorecard
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("OKR Scorecard (Week 2)")] }),
      new Table({
        columnWidths: [600, 5760, 3000],
        rows: [
          new TableRow({ children: [headerCell("#", 600), headerCell("Requirement", 5760), headerCell("Status", 3000)] }),
          ...[ ["1", "Registration \u2192 auto-enrichment \u2192 structured profile", "Done"],
            ["2", "50+ profiles, \u22653 matches each with explanations", "41 profiles (pending Chiara)"],
            ["3", "Unique link, mobile-responsive, no login", "Done"],
            ["4", "Match email with dashboard link", "Done (sandbox)"],
            ["5", "Architecture doc for 2,500 scale", "Done"],
            ["6", "Cost per attendee < \u20AC0.50", "Done (\u20AC0.39)"],
          ].map(row => new TableRow({ children: [
            dataCell(row[0], 600, { center: true, bold: true }),
            dataCell(row[1], 5760),
            dataCell(row[2], 3000, { center: true, color: row[2].startsWith("Done") ? "10B981" : orange }),
          ] })),
        ],
      }),

      // Feedback needed
      new Paragraph({ spacing: { before: 300 }, heading: HeadingLevel.HEADING_1, children: [new TextRun("Feedback Needed")] }),
      ...["Email provider: Victor approved new company AWS account \u2014 when is it ready so I can set up SES?",
        "Chiara: status on attendee data for the 50-profile scale test?",
        "Brainstorm next tier: all Quick Wins shipped \u2014 which Core Features to prioritise? (AI Meeting Prep, Session Matching, Lunch Algorithm, Sponsor Analytics)",
        "Z\u2019s vision: AI-inferred customer matching + company similarity \u2014 start building, or email delivery first?",
      ].map(t => new Paragraph({ numbering: { reference: "feedback", level: 0 }, spacing: { after: 80 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      // separator
      new Paragraph({ spacing: { before: 300, after: 300 }, children: [new TextRun({ text: "\u2501".repeat(60), color: "DDDDDD", size: 16, font: "Arial" })] }),

      // Focus for next week
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Focus for Next Week")] }),
      ...["Set up SES on new company AWS account + verify proofoftalk.io domain",
        "Scale test to 50 profiles (once Chiara provides data)",
        "Full end-to-end journey test with team (magic link \u2192 accept \u2192 mutual match \u2192 chat \u2192 schedule)",
        "Begin AI-inferred customer matching (Z\u2019s vision) or next Core Feature",
      ].map(t => new Paragraph({ numbering: { reference: "focus", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      // Wins
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Wins Worth Celebrating")] }),
      ...["All 5 brainstorm Quick Wins shipped in one week",
        "Magic link access live \u2014 true zero-friction attendee experience",
        'Z\u2019s "who do you want to meet?" vision built and wired into matching',
        "Architecture + cost docs delivered \u2014 system scales to 2,500 at \u20AC0.39/person",
        "QR code renders in email \u2014 scan to see your matches from your phone",
        "ML feedback loop closed \u2014 the engine learns from declines",
        "Complete customer journey mapped (Mermaid diagram)",
      ].map(t => new Paragraph({ numbering: { reference: "wins", level: 0 }, spacing: { after: 60 }, children: [new TextRun({ text: t, size: 21, font: "Arial" })] })),

      // Sign off
      new Paragraph({ spacing: { before: 400 }, children: [new TextRun({ text: "\u2014 Kanyuchi", size: 22, font: "Arial", italics: true, color: gray })] }),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/Users/fadzie/Desktop/Proof_Of_Talk_CD/docs/friday-update-2026-03-28.docx", buf);
  console.log("Done: docs/friday-update-2026-03-28.docx");
});
