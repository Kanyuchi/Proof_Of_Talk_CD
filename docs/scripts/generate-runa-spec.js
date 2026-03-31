const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, Header, Footer, PageNumber, ExternalHyperlink,
} = require("docx");

const tb = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cb = { top: tb, bottom: tb, left: tb, right: tb };
const hdrShade = { fill: "1A1A2E", type: ShadingType.CLEAR };
const accentShade = { fill: "F5F0FF", type: ShadingType.CLEAR };

function p(text, opts = {}) {
  const runs = Array.isArray(text)
    ? text
    : [new TextRun({ text, ...opts.run })];
  return new Paragraph({ children: runs, ...opts.para });
}

function bold(text) { return new TextRun({ text, bold: true }); }
function normal(text) { return new TextRun({ text }); }
function code(text) { return new TextRun({ text, font: "Courier New", size: 18, color: "333333" }); }
function italic(text) { return new TextRun({ text, italics: true }); }

function heading(level, text) {
  return new Paragraph({ heading: level, children: [new TextRun(text)] });
}

function codeBlock(lines) {
  return lines.map(l => new Paragraph({
    spacing: { before: 0, after: 0 },
    shading: { fill: "F4F4F4", type: ShadingType.CLEAR },
    children: [new TextRun({ text: l, font: "Courier New", size: 17, color: "333333" })],
  }));
}

function spacer() { return new Paragraph({ spacing: { before: 60, after: 60 }, children: [] }); }

function tableRow(cells, header = false) {
  return new TableRow({
    tableHeader: header,
    children: cells.map(c => new TableCell({
      borders: cb,
      width: { size: c.w || 2340, type: WidthType.DXA },
      shading: header ? hdrShade : (c.shade || undefined),
      verticalAlign: "center",
      children: [new Paragraph({
        spacing: { before: 40, after: 40 },
        children: Array.isArray(c.t) ? c.t : [new TextRun({
          text: c.t, bold: header, color: header ? "FFFFFF" : "333333", size: header ? 20 : 19, font: "Arial",
        })],
      })],
    })),
  });
}

function simpleTable(headers, rows, widths) {
  return new Table({
    columnWidths: widths,
    rows: [
      tableRow(headers.map((h, i) => ({ t: h, w: widths[i] })), true),
      ...rows.map(r => tableRow(r.map((c, i) => ({ t: c, w: widths[i] })))),
    ],
  });
}

// ── Document ────────────────────────────────────────────────────────────────

const doc = new Document({
  creator: "Kanyuchi",
  title: "Runa x POT Matchmaker - Integration API Specification",
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
      { reference: "num-overview", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "num-timeline", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "num-quickstart", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "num-customer", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: { margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 } },
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "CONFIDENTIAL", size: 16, color: "999999", italics: true })],
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "Runa x POT Matchmaker Integration Spec  |  Page ", size: 16, color: "999999" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "999999" }),
        ],
      })] }),
    },
    children: [
      // ── Title ──
      new Paragraph({ spacing: { after: 80 }, alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "Runa x POT Matchmaker", size: 40, bold: true, color: "1A1A2E" }),
      ] }),
      new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: "Integration API Specification", size: 30, color: "666666" }),
      ] }),
      new Paragraph({ spacing: { after: 60 }, alignment: AlignmentType.CENTER, children: [
        bold("For: "), normal("Swerve (Runa/Extasy developer)    "),
        bold("From: "), normal("Kanyuchi (POT Matchmaker)"),
      ] }),
      new Paragraph({ spacing: { after: 200 }, alignment: AlignmentType.CENTER, children: [
        bold("Date: "), normal("March 31, 2026    "),
        bold("Status: "), new TextRun({ text: "Draft", color: "E76315", bold: true }),
      ] }),

      // ── 1. Overview ──
      heading(HeadingLevel.HEADING_1, "1. Overview"),
      p("The POT Matchmaker is an AI-powered matchmaking engine for Proof of Talk 2026. It matches attendees based on complementary needs, deal-readiness, and non-obvious connections."),
      spacer(),
      p([bold("Goal: "), normal("Allow Runa ticket buyers to seamlessly access their matchmaker dashboard from within Runa \u2014 no separate registration or login required.")]),
      spacer(),
      p([bold("How it works: "), normal("Every attendee has a unique magic link \u2014 a private URL that gives them direct access to their personal matches dashboard. Runa calls our API with the customer's email, gets back their magic link URL, and embeds it as a button or redirect.")]),
      spacer(),
      ...codeBlock([
        "Customer buys ticket on Runa",
        "        \u2193",
        "Customer clicks \"View My Matches\" in Runa",
        "        \u2193",
        "Runa calls:  GET /api/v1/integration/magic-link?email=jane@example.com",
        "        \u2193",
        'We respond:  { "magic_link_url": "https://meet.proofoftalk.io/m/abc123..." }',
        "        \u2193",
        "Runa redirects customer to that URL",
        "        \u2193",
        "Customer lands in their personal matchmaker dashboard",
      ]),

      // ── 2. Base URL ──
      heading(HeadingLevel.HEADING_1, "2. Base URL"),
      ...codeBlock([
        "Production:  https://meet.proofoftalk.io/api/v1",
        "Staging:     http://3.239.218.239/api/v1",
      ]),
      spacer(),
      p([normal("Interactive API docs (Swagger): "), code("{base_url}/docs")]),

      // ── 3. Authentication ──
      heading(HeadingLevel.HEADING_1, "3. Authentication"),
      p([normal("All integration endpoints are protected by an "), bold("API key"), normal(" sent via HTTP header.")]),
      spacer(),
      ...codeBlock(["X-API-Key: your-secret-api-key-here"]),
      spacer(),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("One key per integration partner (Runa gets one key)")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("Key will be shared securely (not via email)")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("All production requests must use HTTPS")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("The key only grants access to /api/v1/integration/* endpoints")] }),

      // ── 4. Endpoints ──
      heading(HeadingLevel.HEADING_1, "4. Endpoints"),

      // Endpoint A
      heading(HeadingLevel.HEADING_2, "Endpoint A: Magic Link Lookup (required)"),
      p([normal("Look up or create an attendee's matchmaker magic link by email.")]),
      spacer(),
      ...codeBlock(["GET /api/v1/integration/magic-link?email={email}"]),
      spacer(),
      p([bold("Query Parameters:")]),
      simpleTable(
        ["Parameter", "Type", "Required", "Description"],
        [
          ["email", "string", "Yes", "Customer's email (case-insensitive)"],
          ["name", "string", "No", "Full name. Required if attendee doesn't exist yet"],
          ["ticket_type", "string", "No", "delegate, sponsor, speaker, or vip. Default: delegate"],
        ],
        [1800, 1200, 1200, 5160],
      ),
      spacer(),
      p([bold("Success Response (200):")]),
      ...codeBlock([
        '{',
        '  "attendee_id": "a1b2c3d4-...",',
        '  "name": "Jane Doe",',
        '  "email": "jane@example.com",',
        '  "magic_link_url": "https://meet.proofoftalk.io/m/abc123...",',
        '  "profile_complete": false,',
        '  "match_count": 8,',
        '  "created_now": false',
        '}',
      ]),
      spacer(),
      simpleTable(
        ["Field", "Description"],
        [
          ["magic_link_url", "The URL to redirect the customer to"],
          ["profile_complete", "true if they've filled in goals + interests"],
          ["match_count", "Number of AI-generated matches (0 if still processing)"],
          ["created_now", "true if attendee was just created on-the-fly"],
        ],
        [2400, 6960],
      ),
      spacer(),
      p([bold("Behaviour when attendee doesn't exist:")]),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        bold("With name provided "), normal("\u2192 We create the attendee instantly, generate their magic link, kick off AI enrichment in the background."),
      ] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        bold("Without name "), normal("\u2192 Returns 404. Always pass name to avoid this."),
      ] }),

      // Endpoint B
      heading(HeadingLevel.HEADING_2, "Endpoint B: Ticket Purchased Webhook (optional)"),
      p("Push ticket purchase data to us in real-time. Creates the attendee immediately so matches are ready before they click \"View Matches\"."),
      spacer(),
      ...codeBlock(["POST /api/v1/integration/ticket-purchased"]),
      spacer(),
      p([bold("Request Body:")]),
      ...codeBlock([
        '{',
        '  "email": "jane@example.com",',
        '  "first_name": "Jane",',
        '  "last_name": "Doe",',
        '  "ticket_type": "vip pass",',
        '  "ticket_code": "TKT-12345",',
        '  "phone": "+33612345678",',
        '  "country": "FRA",',
        '  "city": "Paris",',
        '  "paid_amount": "2500.00",',
        '  "voucher_code": "EARLYBIRD",',
        '  "extasy_order_id": "ord-abc-123",',
        '  "purchased_at": "2026-04-15T10:30:00Z"',
        '}',
      ]),
      spacer(),
      p([bold("Ticket Type Mapping:")]),
      simpleTable(
        ["Runa Ticket Name", "Our Type"],
        [
          ["investor pass", "vip"],
          ["vip pass / vip black pass", "vip"],
          ["general pass", "delegate"],
          ["startup pass", "delegate"],
          ["speaker pass", "speaker"],
          ["sponsor pass", "sponsor"],
        ],
        [5000, 4360],
      ),
      spacer(),
      p([italic("Question for Swerve: "), normal("Are these all the ticket names you use? If you have others, let us know.")]),
      spacer(),
      p("This endpoint is idempotent \u2014 calling it multiple times for the same email won't create duplicates. Safe to retry on network errors."),

      // Endpoint C
      heading(HeadingLevel.HEADING_2, "Endpoint C: Ticket Cancelled (optional)"),
      ...codeBlock(["POST /api/v1/integration/ticket-cancelled"]),
      spacer(),
      p([bold("Request Body: "), code('{ "email": "...", "extasy_order_id": "...", "reason": "refund" }')]),
      p("We deactivate the attendee (excluded from match generation, magic link shows a friendly message)."),

      // Endpoint D
      heading(HeadingLevel.HEADING_2, "Endpoint D: Attendee Status (optional)"),
      p("Check an attendee's matchmaker status. Useful for showing match count inline in Runa."),
      spacer(),
      ...codeBlock(["GET /api/v1/integration/attendee-status?email={email}"]),
      spacer(),
      simpleTable(
        ["Field", "Description"],
        [
          ["has_matches", "Whether the attendee has any AI-generated matches"],
          ["match_count", "Total number of matches"],
          ["mutual_matches", "Both parties accepted \u2014 confirmed connections"],
          ["profile_complete", "Whether they've filled in goals + interests"],
          ["enriched", "Whether our AI pipeline has processed their profile"],
        ],
        [2400, 6960],
      ),
      spacer(),
      p([bold("Use case: "), normal("Display different CTAs in Runa:")]),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        code("profile_complete: false"), normal(" \u2192 \"Complete your matchmaker profile\""),
      ] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        code("match_count > 0"), normal(" \u2192 \"View your 8 matches\""),
      ] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [
        code("mutual_matches > 0"), normal(" \u2192 \"3 people want to meet you!\""),
      ] }),

      // ── 5. Error Format ──
      heading(HeadingLevel.HEADING_1, "5. Error Response Format"),
      ...codeBlock(['{ "detail": "Human-readable error message" }']),
      spacer(),
      simpleTable(
        ["HTTP Status", "Meaning"],
        [
          ["200", "Success"],
          ["201", "Created (new attendee)"],
          ["401", "Missing or invalid API key"],
          ["404", "Attendee not found"],
          ["422", "Validation error"],
          ["429", "Rate limited"],
          ["500", "Server error"],
        ],
        [2400, 6960],
      ),

      // ── 6. Rate Limits ──
      heading(HeadingLevel.HEADING_1, "6. Rate Limits"),
      simpleTable(
        ["Endpoint", "Limit"],
        [
          ["Magic Link Lookup (A)", "100 requests/minute"],
          ["Ticket Purchased (B)", "30 requests/minute"],
          ["Ticket Cancelled (C)", "30 requests/minute"],
          ["Attendee Status (D)", "200 requests/minute"],
        ],
        [5000, 4360],
      ),

      // ── 7. Discussion Points ──
      heading(HeadingLevel.HEADING_1, "7. Discussion Points for Swerve"),
      heading(HeadingLevel.HEADING_3, "7.1 Webhook vs Pull"),
      p("Do you prefer pushing ticket events to us (Endpoints B/C), or should we continue pulling from Extasy daily? Either way, Endpoint A (magic link lookup) is the minimum you need."),
      heading(HeadingLevel.HEADING_3, "7.2 Where does \"View Matches\" live in Runa?"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("Post-purchase confirmation page")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("Ticket dashboard / \"My Tickets\" section")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [normal("Confirmation email")] }),
      heading(HeadingLevel.HEADING_3, "7.3 Redirect vs New Tab vs Iframe"),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Redirect (recommended) "), normal("\u2014 window.location.href = magic_link_url")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("New tab "), normal("\u2014 window.open(magic_link_url, '_blank')")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [bold("Iframe "), normal("\u2014 Not recommended; requires CORS changes on our side")] }),
      heading(HeadingLevel.HEADING_3, "7.4 Ticket Type Mapping"),
      p("Please confirm the ticket names in section 4B match what Runa uses."),
      heading(HeadingLevel.HEADING_3, "7.5 Showing Matchmaker Data in Runa"),
      p("Want to show match count inline? Use Endpoint D. Just need a redirect button? Endpoint A alone is sufficient."),

      // ── 8. Timeline ──
      heading(HeadingLevel.HEADING_1, "8. Implementation Timeline"),
      simpleTable(
        ["Step", "Owner", "Description"],
        [
          ["1", "Swerve", "Review this spec, confirm approach"],
          ["2", "Kanyuchi", "Build Endpoints A\u2013D, deploy to staging"],
          ["3", "Kanyuchi", "Share staging API key + test data"],
          ["4", "Swerve", "Integrate Endpoint A into Runa"],
          ["5", "Both", "End-to-end test: buy ticket \u2192 view matches"],
          ["6", "Both", "Ship to production"],
        ],
        [1200, 1800, 6360],
      ),

      // ── 9. Quick Start ──
      heading(HeadingLevel.HEADING_1, "9. Quick Start for Swerve"),
      p([bold("Minimum integration (15 minutes of work):")]),
      spacer(),
      new Paragraph({ numbering: { reference: "num-quickstart", level: 0 }, children: [normal("Get API key from Kanyuchi")] }),
      new Paragraph({ numbering: { reference: "num-quickstart", level: 0 }, children: [normal("When customer clicks \"View Matches\":")] }),
      ...codeBlock([
        'const response = await fetch(',
        '  `https://meet.proofoftalk.io/api/v1/integration/magic-link',
        '    ?email=${customerEmail}&name=${customerName}&ticket_type=${ticketType}`,',
        '  { headers: { "X-API-Key": API_KEY } }',
        ');',
        'const { magic_link_url } = await response.json();',
        'window.location.href = magic_link_url;',
      ]),
      new Paragraph({ numbering: { reference: "num-quickstart", level: 0 }, children: [bold("Done. "), normal("Customer lands in their matchmaker dashboard.")] }),
      spacer(),
      spacer(),
      p([bold("Questions? "), normal("Reach out to Kanyuchi.")], { para: { alignment: AlignmentType.CENTER } }),
    ],
  }],
});

const outPath = "/Users/fadzie/Desktop/Proof_Of_Talk_CD/docs/runa-integration-spec.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("Created:", outPath);
});
