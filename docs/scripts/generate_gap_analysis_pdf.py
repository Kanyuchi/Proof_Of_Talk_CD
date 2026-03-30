"""Generate the Data Completeness Gap Analysis PDF for POT Matchmaker."""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Colours ──────────────────────────────────────────────────────────────────
DARK_BG   = colors.HexColor("#0F0F13")
AMBER     = colors.HexColor("#F59E0B")
AMBER_LT  = colors.HexColor("#FCD34D")
DEEP_GRAY = colors.HexColor("#1C1C24")
MID_GRAY  = colors.HexColor("#2A2A36")
LIGHT_GRAY= colors.HexColor("#6B7280")
OFF_WHITE = colors.HexColor("#F3F4F6")
RED_SOFT  = colors.HexColor("#EF4444")
GREEN_SOFT= colors.HexColor("#10B981")
ORANGE    = colors.HexColor("#F97316")
WHITE     = colors.white
BLACK     = colors.HexColor("#111111")
SLATE     = colors.HexColor("#1E293B")

# ── Styles ───────────────────────────────────────────────────────────────────
def styles():
    from reportlab.lib.styles import getSampleStyleSheet
    base = getSampleStyleSheet()

    return {
        "cover_title": ParagraphStyle("cover_title",
            fontName="Helvetica-Bold", fontSize=26, leading=32,
            textColor=WHITE, spaceAfter=6),
        "cover_sub": ParagraphStyle("cover_sub",
            fontName="Helvetica", fontSize=12, leading=16,
            textColor=AMBER, spaceAfter=4),
        "cover_meta": ParagraphStyle("cover_meta",
            fontName="Helvetica", fontSize=9, leading=13,
            textColor=LIGHT_GRAY),
        "section_h": ParagraphStyle("section_h",
            fontName="Helvetica-Bold", fontSize=13, leading=18,
            textColor=AMBER, spaceBefore=14, spaceAfter=6),
        "sub_h": ParagraphStyle("sub_h",
            fontName="Helvetica-Bold", fontSize=10, leading=14,
            textColor=OFF_WHITE, spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9, leading=14,
            textColor=OFF_WHITE, spaceAfter=5),
        "body_small": ParagraphStyle("body_small",
            fontName="Helvetica", fontSize=8, leading=12,
            textColor=LIGHT_GRAY, spaceAfter=3),
        "bullet": ParagraphStyle("bullet",
            fontName="Helvetica", fontSize=9, leading=14,
            textColor=OFF_WHITE, leftIndent=12, bulletIndent=0,
            spaceAfter=3),
        "code": ParagraphStyle("code",
            fontName="Courier", fontSize=8, leading=12,
            textColor=AMBER_LT, spaceAfter=3),
        "pill_green": ParagraphStyle("pill_green",
            fontName="Helvetica-Bold", fontSize=8,
            textColor=GREEN_SOFT),
        "pill_red": ParagraphStyle("pill_red",
            fontName="Helvetica-Bold", fontSize=8,
            textColor=RED_SOFT),
        "pill_orange": ParagraphStyle("pill_orange",
            fontName="Helvetica-Bold", fontSize=8,
            textColor=ORANGE),
        "footer": ParagraphStyle("footer",
            fontName="Helvetica", fontSize=7, leading=10,
            textColor=LIGHT_GRAY, alignment=TA_CENTER),
    }

S = styles()

# ── Document setup ────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

doc = SimpleDocTemplate(
    "/Users/fadzie/Desktop/Proof_Of_Talk_CD/docs/POT_Gap_Analysis.pdf",
    pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=MARGIN, bottomMargin=20 * mm,
    title="Data Completeness Gap Analysis — POT Matchmaker",
    author="Kanyuchi",
    subject="Extasy API vs Matching Engine Requirements",
)

story = []

# ── Helper: divider ───────────────────────────────────────────────────────────
def divider(color=MID_GRAY, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6, spaceBefore=2)

def amber_divider():
    return HRFlowable(width="100%", thickness=1.5, color=AMBER, spaceAfter=8, spaceBefore=4)

def section(title):
    return [amber_divider(), Paragraph(title, S["section_h"])]

# ── COVER BLOCK ───────────────────────────────────────────────────────────────
# Dark header panel via a single-cell table
cover_data = [[
    Paragraph("DATA COMPLETENESS GAP ANALYSIS", S["cover_sub"]),
]]
cover_table = Table(cover_data, colWidths=[PAGE_W - 2 * MARGIN])
cover_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), DARK_BG),
    ("TOPPADDING", (0,0), (-1,-1), 8),
    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 10),
    ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ("ROUNDEDCORNERS", (0,0), (-1,-1), 4),
]))
story.append(cover_table)
story.append(Spacer(1, 4))

title_data = [[Paragraph(
    "Extasy API&nbsp;&nbsp;<font color='#6B7280'>vs</font>&nbsp;&nbsp;Matching Engine Requirements",
    S["cover_title"]
)]]
title_table = Table(title_data, colWidths=[PAGE_W - 2 * MARGIN])
title_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), DARK_BG),
    ("TOPPADDING", (0,0), (-1,-1), 10),
    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ("LEFTPADDING", (0,0), (-1,-1), 10),
    ("RIGHTPADDING", (0,0), (-1,-1), 10),
]))
story.append(title_table)
story.append(Spacer(1, 4))

meta_data = [[
    Paragraph("Project: POT Matchmaker — Proof of Talk 2026", S["cover_meta"]),
    Paragraph("Author: Kanyuchi", S["cover_meta"]),
    Paragraph("Date: March 2026", S["cover_meta"]),
]]
meta_table = Table(meta_data, colWidths=[(PAGE_W - 2*MARGIN)/3]*3)
meta_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), DEEP_GRAY),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ("LEFTPADDING", (0,0), (-1,-1), 10),
    ("RIGHTPADDING", (0,0), (-1,-1), 10),
]))
story.append(meta_table)
story.append(Spacer(1, 14))

# ── CONTEXT ───────────────────────────────────────────────────────────────────
story += section("Context")
story.append(Paragraph(
    "We have <b>15 confirmed PAID attendees</b> from the Extasy ticketing API. "
    "The question is whether this data is sufficient to power the POT Matchmaker AI engine. "
    "The answer is: <b>it covers identity only — approximately 15% of what the engine actually needs.</b> "
    "This document maps the gaps and defines a 3-layer strategy to close them before the event.",
    S["body"]
))

# Summary stat boxes
stat_data = [
    [Paragraph("<b>15</b>\nConfirmed PAID\nattendees", S["sub_h"]),
     Paragraph("<b>~15%</b>\nData coverage\nfrom Extasy alone", S["sub_h"]),
     Paragraph("<b>3 layers</b>\nGap closure\nstrategy", S["sub_h"]),
     Paragraph("<b>June 2–3</b>\nLouvre Palace\nParis", S["sub_h"])],
]
stat_table = Table(stat_data, colWidths=[(PAGE_W - 2*MARGIN)/4]*4)
stat_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), DEEP_GRAY),
    ("TOPPADDING", (0,0), (-1,-1), 10),
    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("BOX", (0,0), (0,-1), 0.5, AMBER),
    ("BOX", (1,0), (1,-1), 0.5, MID_GRAY),
    ("BOX", (2,0), (2,-1), 0.5, MID_GRAY),
    ("BOX", (3,0), (3,-1), 0.5, MID_GRAY),
    ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(Spacer(1, 6))
story.append(stat_table)
story.append(Spacer(1, 10))

# ── WHAT EXTASY PROVIDES ──────────────────────────────────────────────────────
story += section("What Extasy Provides (Per Attendee)")

headers = [
    Paragraph("<b>Field</b>", S["sub_h"]),
    Paragraph("<b>Available</b>", S["sub_h"]),
    Paragraph("<b>Quality</b>", S["sub_h"]),
    Paragraph("<b>Notes</b>", S["sub_h"]),
]

rows = [headers] + [
    [Paragraph(f, S["body"]), Paragraph(a, s), Paragraph(q, S["body"]), Paragraph(n, S["body_small"])]
    for f, a, s, q, n in [
        ("name",                   "✓ Yes",    S["pill_green"],  "Good",   "First + last from registration"),
        ("email",                  "✓ Yes",    S["pill_green"],  "Good",   "Enables all downstream enrichment"),
        ("phone_number",           "✓ Yes",    S["pill_green"],  "Good",   "Useful for direct contact"),
        ("ticket_type",            "✓ Yes",    S["pill_green"],  "Good",   "Maps to vip / delegate / speaker / sponsor"),
        ("city / country",         "✓ Yes",    S["pill_green"],  "Good",   "ISO3 country code + city name"),
        ("bought_date",            "✓ Yes",    S["pill_green"],  "Good",   "Useful for prioritisation"),
        ("company",                "⚠ Partial", S["pill_orange"], "Weak",   "Inferred from email domain only (e.g. @kraken.com → Kraken)"),
        ("title",                  "✗ No",     S["pill_red"],    "—",      "Not in API — must be enriched or self-reported"),
        ("interests",              "✗ No",     S["pill_red"],    "—",      "Not in API — core input to embedding"),
        ("goals",                  "✗ No",     S["pill_red"],    "—",      "Not in API — highest signal field for matching"),
        ("seeking / not_looking",  "✗ No",     S["pill_red"],    "—",      "Not in API — used for hard filter in Stage 2"),
        ("preferred_geographies",  "✗ No",     S["pill_red"],    "—",      "Not in API — optional hard filter"),
        ("deal_stage",             "✗ No",     S["pill_red"],    "—",      "Not in API — critical for deal-ready matching"),
        ("linkedin_url",           "✗ No",     S["pill_red"],    "—",      "Not in API — unlocks LinkedIn enrichment via Proxycurl"),
        ("twitter_handle",         "✗ No",     S["pill_red"],    "—",      "Not in API — unlocks real-time activity enrichment"),
    ]
]

col_w = PAGE_W - 2*MARGIN
field_table = Table(rows, colWidths=[col_w*0.22, col_w*0.13, col_w*0.12, col_w*0.53])
field_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), SLATE),
    ("BACKGROUND", (0,1), (-1,1), DEEP_GRAY),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [DEEP_GRAY, MID_GRAY]),
    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#333344")),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(field_table)
story.append(Spacer(1, 10))

# ── WHAT THE MATCHING ENGINE NEEDS ───────────────────────────────────────────
story += section("What the Matching Engine Actually Needs")

story.append(Paragraph("Hard Requirements (engine will not run without these)", S["sub_h"]))
reqs = [
    ("embedding", "1536-dim vector — generated from composite profile text via OpenAI text-embedding-3-small"),
    ("ai_summary", "GPT-4o generated — 2–3 sentence professional summary, key input to composite text"),
    ("intent_tags", "GPT-4o classified — used as hard filter in Stage 2 candidate retrieval"),
    ("ticket_type", "Used for eligibility filtering — Extasy provides this ✓"),
]
req_rows = [[Paragraph(f"<b>{k}</b>", S["body"]), Paragraph(v, S["body_small"])] for k, v in reqs]
req_table = Table(req_rows, colWidths=[col_w*0.22, col_w*0.78])
req_table.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0,0), (-1,-1), [DEEP_GRAY, MID_GRAY]),
    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#333344")),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("BACKGROUND", (0,3), (-1,3), colors.HexColor("#0D2B1A")),  # green tint for the one we have
]))
story.append(req_table)
story.append(Spacer(1, 8))

story.append(Paragraph("Composite Text Inputs (fed to OpenAI for embedding generation)", S["sub_h"]))
story.append(Paragraph(
    "The richer these fields are, the better the match quality. They are concatenated into a "
    "single text blob and embedded as a 1536-dim vector:",
    S["body"]
))
composite_fields = [
    ("name, title, company", "Extasy has name only — title and company are absent or inferred"),
    ("interests, goals", "Completely absent from Extasy — highest signal inputs"),
    ("ai_summary", "Generated by GPT-4o after other fields are populated"),
    ("linkedin_summary", "From Proxycurl enrichment — requires PROXYCURL_API_KEY"),
    ("company_description", "From website scraping — no API key needed"),
    ("recent_activity", "From Twitter/X enrichment — requires TWITTER_BEARER_TOKEN"),
    ("funding_info", "From Crunchbase scraping — no API key needed"),
]
cf_rows = [[Paragraph(f"<b>{k}</b>", S["body"]), Paragraph(v, S["body_small"])] for k, v in composite_fields]
cf_table = Table(cf_rows, colWidths=[col_w*0.28, col_w*0.72])
cf_table.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0,0), (-1,-1), [DEEP_GRAY, MID_GRAY]),
    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#333344")),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(cf_table)
story.append(Spacer(1, 10))

# ── GAP CLOSURE STRATEGY ──────────────────────────────────────────────────────
story += section("Gap Closure Strategy — 3-Layer Approach")

layers = [
    (
        "Layer 1 — Email-Domain Enrichment",
        "Immediate · No API keys required",
        GREEN_SOFT,
        [
            "Infer company name and website URL from email domain (already implemented in ingest script).",
            "Examples from current 15 attendees:",
            "  kaushik.sthankiya@kraken.com → Kraken (crypto exchange) · https://kraken.com",
            "  nmehta@clearstreet.io → Clear Street (prime brokerage) · https://clearstreet.io",
            "  robin.s@kucoin.com → KuCoin (crypto exchange) · https://kucoin.com",
            "  laurence@theqrl.org → QRL (quantum-resistant blockchain) · https://theqrl.org",
            "  dariia.p@eternax.ai → Eternax (AI/Web3) · https://eternax.ai",
            "Outcome: company_website field populated → enables Layer 2 website scraping.",
        ]
    ),
    (
        "Layer 2 — Enrichment Pipeline",
        "Runs post-ingestion · Company website scraping requires no API key",
        AMBER,
        [
            "Company website scraping (no API key needed) — uses httpx + BeautifulSoup:",
            "  Extracts: company description, sector, product positioning from meta tags and body text.",
            "LinkedIn via Proxycurl (requires PROXYCURL_API_KEY):",
            "  Extracts: title, career history, headline, skills, linkedin_summary.",
            "Twitter/X API (requires TWITTER_BEARER_TOKEN):",
            "  Extracts: recent_activity, positioning, informal interests.",
            "Crunchbase scraping (no API key needed for basic data):",
            "  Extracts: funding rounds, total raised, investor names, sector categories.",
            "Run command: python scripts/enrich_and_embed.py",
        ]
    ),
    (
        "Layer 3 — Attendee Onboarding Form",
        "Highest signal · Most work · Implemented at /onboarding",
        colors.HexColor("#8B5CF6"),
        [
            "A lightweight post-purchase form sent to confirmed attendees collecting:",
            "  title + company (confirm or correct the inferred values)",
            "  goals — 'What do you want to achieve at POT 2026?'",
            "  interests — select from a curated taxonomy (15 topics)",
            "  deal_stage — are you raising, deploying, building?",
            "  seeking — who do you want to meet?",
            "  linkedin_url (optional — triggers Proxycurl enrichment)",
            "This is the strategy used by Brella and other tier-1 event matchmakers.",
            "Without this layer, the engine falls back entirely on enrichment inference.",
            "With this layer, match quality is equivalent to the 5 seed-profile demo.",
        ]
    ),
]

for title, subtitle, accent_color, bullets in layers:
    layer_data = [[
        Paragraph(f"<b>{title}</b>", S["sub_h"]),
        Paragraph(subtitle, S["body_small"]),
    ]]
    layer_header = Table(layer_data, colWidths=[col_w*0.55, col_w*0.45])
    layer_header.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SLATE),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (0,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("LINEBEFORE", (0,0), (0,-1), 3, accent_color),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
    ]))
    story.append(layer_header)

    bullet_rows = [[Paragraph(f"{'  ' if b.startswith('  ') else '→ '}{b.strip()}", S["bullet"])] for b in bullets]
    bullet_table = Table(bullet_rows, colWidths=[col_w])
    bullet_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DEEP_GRAY),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE", (0,0), (0,-1), 1.5, accent_color),
    ]))
    story.append(bullet_table)
    story.append(Spacer(1, 8))

# ── MATCH QUALITY MATRIX ──────────────────────────────────────────────────────
story += section("Expected Match Quality by Data Layer")

story.append(Paragraph(
    "The table below shows the expected match quality at each stage of data enrichment:",
    S["body"]
))

quality_headers = [
    Paragraph("<b>Data State</b>", S["sub_h"]),
    Paragraph("<b>Composite Text Quality</b>", S["sub_h"]),
    Paragraph("<b>Match Quality</b>", S["sub_h"]),
    Paragraph("<b>Verdict</b>", S["sub_h"]),
]
quality_rows = [quality_headers] + [
    [Paragraph(a, S["body"]), Paragraph(b, S["body_small"]), Paragraph(c, S["body"]), Paragraph(d, S["body"])]
    for a, b, c, d in [
        ("Extasy only\n(no enrichment)",
         "Name: X, Ticket Type: vip\n— almost nothing",
         "Very low — essentially\nrandom within tier",
         "❌ Not viable"),
        ("+ Website scraping\n(Layer 2, no API keys)",
         "Adds company description,\nsector, rough positioning",
         "Sector-level accurate\nbut not deal-ready",
         "⚠ Functional but shallow"),
        ("+ LinkedIn enrichment\n(Proxycurl, Layer 2)",
         "Adds title, career history,\nprofessional positioning",
         "Good — intent tags\nbecome meaningful",
         "✓ Production ready"),
        ("+ Onboarding form\n(Layer 3)",
         "Full composite profile —\nequivalent to seed profiles",
         "Best — matches on par\nwith the demo",
         "✓✓ Optimal"),
    ]
]

q_table = Table(quality_rows, colWidths=[col_w*0.22, col_w*0.30, col_w*0.25, col_w*0.23])
q_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), SLATE),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [DEEP_GRAY, MID_GRAY]),
    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#333344")),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    # Color code the verdict column
    ("TEXTCOLOR", (3,1), (3,1), RED_SOFT),
    ("TEXTCOLOR", (3,2), (3,2), ORANGE),
    ("TEXTCOLOR", (3,3), (3,3), GREEN_SOFT),
    ("TEXTCOLOR", (3,4), (3,4), AMBER),
]))
story.append(q_table)
story.append(Spacer(1, 10))

# ── IMPLEMENTATION PLAN ───────────────────────────────────────────────────────
story += section("Recommended Implementation Plan")

steps = [
    ("Step 1", "Run schema migration in Supabase",
     "File: backend/scripts/supabase_setup.sql — run in Supabase SQL editor",
     "Blocked on DB credentials", ORANGE),
    ("Step 2", "Run Extasy ingestion",
     "python scripts/ingest_extasy.py\nResult: 15 attendees in Supabase with identity + company_website fields",
     "Ready", GREEN_SOFT),
    ("Step 3", "Run website scraping enrichment (no API keys needed)",
     "python scripts/enrich_and_embed.py --scrape-only\nResult: company_description added to enriched_profile for each attendee",
     "Ready", GREEN_SOFT),
    ("Step 4", "Run AI summary + intent classification + embedding generation",
     "python scripts/enrich_and_embed.py\nResult: ai_summary, intent_tags, embedding, deal_readiness_score populated",
     "Needs OPENAI_API_KEY", AMBER),
    ("Step 5", "Generate matches",
     "POST /api/matches/generate-all via admin dashboard\nResult: match pairs with scores + GPT-4o explanations",
     "Ready after Step 4", AMBER),
    ("Step 6", "Proxycurl LinkedIn enrichment (optional but high-value)",
     "Set PROXYCURL_API_KEY in backend/.env, then re-run python scripts/enrich_and_embed.py --force\nResult: title, career history, linkedin_summary added → significantly richer profiles",
     "Optional — needs API key", LIGHT_GRAY),
    ("Step 7", "Attendee onboarding form (highest value — now built)",
     "Send /onboarding link to all 15 confirmed attendees post-purchase\nURL: https://app.proofoftalk.io/onboarding\nAuth: Extasy ticket code (printed on confirmation email)\nCollects: title, company, goals, interests, deal_stage, seeking, linkedin_url",
     "Live — highest priority", GREEN_SOFT),
]

for num, title, detail, status, color in steps:
    step_data = [[
        Paragraph(f"<b>{num}</b>", S["sub_h"]),
        Paragraph(f"<b>{title}</b>", S["sub_h"]),
        Paragraph(status, S["body_small"]),
    ]]
    step_header = Table(step_data, colWidths=[col_w*0.10, col_w*0.60, col_w*0.30])
    step_header.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), SLATE),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("LINEBEFORE", (0,0), (0,-1), 3, color),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (2,0), (2,-1), "RIGHT"),
        ("TEXTCOLOR", (2,0), (2,-1), color),
    ]))

    detail_data = [[Paragraph(detail, S["body_small"])]]
    detail_table = Table(detail_data, colWidths=[col_w])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DEEP_GRAY),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE", (0,0), (0,-1), 1.5, color),
    ]))
    story.append(KeepTogether([step_header, detail_table]))
    story.append(Spacer(1, 4))

story.append(Spacer(1, 8))

# ── CRITICAL FILES ────────────────────────────────────────────────────────────
story += section("Critical Files")

files = [
    ("backend/app/services/matching.py",    "3-stage matching pipeline (Embed → Retrieve → Rank & Explain)"),
    ("backend/app/services/enrichment.py",  "Multi-source enrichment (LinkedIn, Twitter, website scraping, Crunchbase)"),
    ("backend/app/services/embeddings.py",  "Composite text builder + OpenAI embedding + AI summary + intent classifier"),
    ("backend/app/models/attendee.py",      "Full field definitions for Attendee and Match SQLAlchemy models"),
    ("backend/data/seed_profiles.json",     "Reference for what a complete profile looks like (5 demo attendees)"),
    ("backend/scripts/ingest_extasy.py",    "Extasy API → Supabase ingestion script (sets company_website from domain)"),
    ("backend/scripts/enrich_and_embed.py", "Standalone batch enrichment + embedding script (no FastAPI server needed)"),
    ("backend/scripts/supabase_setup.sql",  "Schema migration — run once in Supabase SQL editor"),
    ("frontend/src/pages/Onboarding.tsx",   "3-step post-purchase attendee onboarding form (/onboarding route)"),
]

file_rows = [[Paragraph(f, S["code"]), Paragraph(d, S["body_small"])] for f, d in files]
file_table = Table(file_rows, colWidths=[col_w*0.45, col_w*0.55])
file_table.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0,0), (-1,-1), [DEEP_GRAY, MID_GRAY]),
    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#333344")),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(file_table)
story.append(Spacer(1, 10))

# ── VERIFICATION CHECKLIST ────────────────────────────────────────────────────
story += section("Verification Checklist")
story.append(Paragraph("After Steps 2–5 are complete, confirm via these API calls:", S["body"]))

checks = [
    ("GET /api/attendees",             "Returns 15 real attendees from Supabase (not seed data)"),
    ("GET /api/attendees/{id}",        "enriched_profile.company_description is populated for most attendees"),
    ("GET /api/attendees/{id}",        "ai_summary, intent_tags, deal_readiness_score are non-null"),
    ("GET /api/matches/{attendee_id}", "Match pairs returned with GPT-4o explanations and overall_score > 0.60"),
    ("GET /api/dashboard/stats",       "Dashboard shows real attendee counts and enrichment coverage %"),
]

check_rows = [[Paragraph(f"→  <b>{e}</b>", S["body"]), Paragraph(d, S["body_small"])] for e, d in checks]
check_table = Table(check_rows, colWidths=[col_w*0.38, col_w*0.62])
check_table.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0,0), (-1,-1), [DEEP_GRAY, MID_GRAY]),
    ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#333344")),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(check_table)
story.append(Spacer(1, 10))

# ── FOOTER ────────────────────────────────────────────────────────────────────
story.append(divider(AMBER))
story.append(Paragraph(
    "POT Matchmaker · XVentures Labs Internal Entrepreneur · Level 3 Submission · "
    "Proof of Talk 2026 · Louvre Palace, Paris · June 2–3, 2026",
    S["footer"]
))

# ── Page background + footer function ────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # Dark background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Amber top stripe
    canvas.setFillColor(AMBER)
    canvas.rect(0, PAGE_H - 3, PAGE_W, 3, fill=1, stroke=0)
    # Page number
    canvas.setFillColor(LIGHT_GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()

doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("PDF generated: docs/POT_Gap_Analysis.pdf")
