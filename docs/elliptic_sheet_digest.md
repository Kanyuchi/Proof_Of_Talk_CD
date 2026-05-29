# Elliptic Sheet Digest

**Source file:** `/tmp/elliptic_sheet.txt` (1554 lines)
**Google Sheet:** "Proof of Talk Paris event booklet" (`1g40iZM_utxjG_aPzynDmOwny8g_iQKv0FAHyj6RWE5I`)
**Owner:** millie.waxman@elliptic.co

---

## TOP-LEVEL SUMMARY (read this first)

- **Tab 3 (Aylin's intro list, lines 136-170) is the ONLY tab with a Request Meeting owner column.** 34 data rows total; 33 are assigned to "Aylin Zanier" (full name, not just "Aylin"), 0 rows are assigned to Ylli or Oliver. Lines 171-761 are the same sheet's long tail of ALL PoT attendees (Organisation + Job Title only, no owner, no intro reason) - these are NOT priority intro requests and should NOT be ingested as intros.
- **Tabs 4 and 5 (lines 763-794 and 806-896) are Ylli's priority ICP intelligence list**, structured as company + segment + location + titles + tier + "Why Meet?" rationale + owner column. These use "Ylli", "Simone or James?", and "James?" as owner values - owner column is ambiguous for non-Ylli rows. Oliver's rows appear in the overlapping NO_HEADER continuation table (lines 798-804).
- **Bpifrance appears twice in Aylin's tab** (lines 144-145) and Byzantine Fi / Byzantine Finance appear twice as slightly different company name variants (lines 146-147). Dedup logic needed.
- **Three Elliptic staff confirmed in Luma RSVP tab:** aylin.zanier@elliptic.co (line 85), ylli@elliptic.co (line 80). No oliver@elliptic.co found anywhere in the file.
- **The last two tabs (lines 1394-1554) are a speakers/VIP list and a partners grid** - no owner column, not ingest candidates for priority intros.

---

## 1. TAB INVENTORY

### Tab 1 - "Meeting Log" (CRM-style pre-booked meetings)
- **Lines:** 1-50
- **Header (line 1):** `| Meeting Type | Date / Time | First Name | Last Name | Company Name | Job Title | Email | Country | Industry | Mobile Number | Booked By | Elliptic Attendees | Executive Attendees | Notes | Did they attend | Follow up meeting booked | Record Owner (Responsible for follow up) | Contact Nature | Event member status | lead Source | Lead Source Detail | Associated Events Tally |`
- **Data rows:** 3 (lines 3-5; lines 6-50 are blank rows with only "Event / Name of the Event" filler in last 3 cols)
- **Owner breakdown (col "Booked By"):** Oliver: 3, blank: 47
- **Status: INGEST** - 3 real meeting rows, all owned by Oliver. Rich schema with email, company, title, booked-by, notes.

### Tab 2 - "Luma RSVP" (event guest list)
- **Lines:** 52-134
- **Header (line 52):** `| guest_id | name | first_name | last_name | email | phone_number | created_at | approval_status | checked_in_at | utm_source | qr_code_url | What company do you work for? | What is your job title? | What is your LinkedIn profile? | What is your X (Twitter) handle? |`
- **Data rows:** 82 (lines 54-134)
- **Owner breakdown:** No owner column. This is the raw Luma RSVP export.
- **Status: SKIP for priority intros** - This is the Luma guest list for the PoT event, not Elliptic's intro requests. Useful for matching attendees in the matchmaker but not an intro-request source.

### Tab 3 - "Aylin's Priority Intro Requests" (+ full attendee tail)
- **Lines:** 136-761
- **Header (line 136):** `| Organization | Job Title | Request Meeting | Reason for introduction. |`
- **Data rows with a "Request Meeting" value:** 33 rows, lines 138-170 (all "Aylin Zanier")
- **Data rows with BLANK "Request Meeting":** ~592 rows, lines 171-761 - these are the full PoT attendee list (Organisation + Job Title only, no intro reason, no owner). These are NOT intro requests.
- **Owner breakdown (col 3 = "Request Meeting"):** "Aylin Zanier": 33, blank: ~592
- **Status: INGEST lines 138-170 only** - Only the 33 named rows are priority intros. The blank-owner tail should be skipped or treated as a separate "all attendees" reference.

### Tab 4 - "Ylli's ICP Meeting List" (first instance)
- **Lines:** 763-794
- **Header (line 763):** `| Company | ICP Segment | HQ / Location | Title(s) from List | Priority Action | Why Meet? | (owner col, col 7) |`
- **Data rows:** 31 (lines 765-794)
- **Owner breakdown (col 7):** Ylli: 25, "Simone or James?": 1 (Qivalis), "James?": 1 (UBS), Oliver: 4 (lines 798-804 in the NO_HEADER continuation), blank: 0
- **Status: INGEST** - Structured ICP intelligence with tier ratings, HQ, and "Why Meet?" rationale. Note: this table continues into Tab 5 (NO_HEADER section, lines 796-804) for Oliver's rows.

### Tab 4a - NO_HEADER continuation (Oliver's ICP rows)
- **Lines:** 796-804
- **Header:** `NO_HEADER` (same schema as Tab 4 - 7 columns)
- **Data rows:** 7 (lines 798-804)
- **Owner breakdown:** Oliver: 7
- **Status: INGEST** - Oliver's ICP rows separated from Tab 4 by a blank line and NO_HEADER marker. Same schema as Tab 4.

### Tab 5 - "Ylli's Full ICP Intelligence List" (second, longer instance)
- **Lines:** 806-896
- **Header (line 806):** `| Company | ICP Segment | HQ / Location | Title(s) from List | Priority Action | Why Meet? | (owner col) |`
- **Data rows:** 90 (lines 808-896)
- **Owner breakdown:** Ylli: 65+, "Simone or James?": 1 (Qivalis), "James?": 1 (UBS), Oliver: 3, blank (unassigned companies): ~20
- **Note:** This appears to be an EXPANDED version of Tab 4 - it includes all of Tab 4's rows PLUS additional companies. The two tabs have substantial overlap (all Tab 4 Ylli/Oliver rows recur here). The blank-owner rows (lines 850-896) cover a large number of Banks/FI and CEX companies from the full attendee list.
- **Status: INGEST as the canonical version** - Tab 4 is a subset; Tab 5 is the master. De-duplicate against Tab 4 on company name.

### Tab 5a - NO_HEADER continuation (blank-owner ICP companies, batch 1)
- **Lines:** 898-896** (immediately follows Tab 5)**

Actually re-examining: lines 898-1256 are a large NO_HEADER table that continues the ICP intelligence format, covering RWA, Security, Staking, Startups, Service Providers, etc., all with blank owner column. This is part of the same ICP sheet.

### Tab 5b - NO_HEADER continuation (long tail of ICP companies, no owner)
- **Lines:** 898-1255
- **Header:** `NO_HEADER` (same 6-column schema: Company | ICP Segment | HQ | Titles | Priority Action | Why Meet?)
- **Data rows:** ~356 (lines 900-1255)
- **Owner breakdown:** All blank in owner column
- **Status: INGEST** - Useful ICP intelligence even without owners; tier ratings and "Why Meet?" rationale are complete.

### Tab 6 - "Ledger special entry" (single-row table with header)
- **Lines:** 1257-1268
- **Header (line 1257):** `| Ledger | CEX / Hardware | Paris, France | Head of Trading, CEO, Board Member, BD, Partnerships, Finance | Tier 1 — leading hardware wallet enterprise | ... |`
- **Note:** Line 1257 is actually a DATA row, not a proper header (the separator is on line 1258). This is a malformed table - the Ledger row was exported as the header. Lines 1259-1268 are additional data rows.
- **Data rows:** 11 (lines 1257, 1259-1268) - includes Ledger, Nexo, YouHodler, Flowdesk, GSR, XBTO (x2), American Bitcoin, B2C2, Volta Wallet, SwissBorg
- **Owner breakdown:** No owner column (6 cols only)
- **Status: INGEST** - High-priority Tier 1 companies. Merge into the main ICP intelligence table.

### Tab 7 - "Speakers / VIP List"
- **Lines:** 1394-1539
- **Header (line 1394):** `| First Name | Last Name | Job Title | Organization |`
- **Data rows:** 145 (lines 1396-1539)
- **Owner breakdown:** No owner column.
- **Status: SKIP for priority intros** - This is the speaker/VIP booking list. Not an intro-request source. Useful for checking whether a priority intro target is already a confirmed speaker.

### Tab 8 - "Partners Grid" (unstructured)
- **Lines:** 1540-1554
- **Header:** `NO_HEADER` or "Partners" label (line 1540 = `| Partners |  |  |  |`)
- **Data rows:** 14 rows of 4-column partner name grids
- **Owner breakdown:** N/A
- **Status: SKIP** - Flat list of company names in a 4-column grid. Not structured data; no owner, no titles, no contact info.

---

## 2. PER-INGEST-TAB SCHEMA

### Tab 1 - Meeting Log (lines 3-5)

**Column mapping:**
| Col | Header | Maps to |
|-----|--------|---------|
| 1 | Meeting Type | `meeting_type` (e.g. "Prebooked meeting") |
| 2 | Date / Time | `scheduled_datetime_raw` |
| 3 | First Name | `first_name` |
| 4 | Last Name | `last_name` |
| 5 | Company Name | `target_company_raw` |
| 6 | Job Title | `target_title_raw` |
| 7 | Email | `contact_email` |
| 8 | Country | `country` |
| 9 | Industry | `industry_raw` |
| 10 | Mobile Number | `phone` (all blank) |
| 11 | Booked By | `elliptic_owner` (= "Oliver" for all 3) |
| 12-22 | Elliptic Attendees ... Associated Events | mostly blank; discard |

**Sample rows (all 3 data rows):**
1. `Prebooked meeting | 3 June 13:00 | Leonardo | Larieira | Teroxx | Digital Assets Investment Strategist | leonardo.larieira@teroxx.com | Cyprus | Crypto Native | | Oliver`
2. `Prebooked meeting | 17 June 09:00 | Niki | Charilaou | Bank of Cyprus | Manager Financial Crime & Sanctions Compliance | niki.charilaou@bankofcyprus.com | Cyprus | Traditional Corporates | | Oliver`
3. `Prebooked meeting | 8 June 13:00 | Iain | Armstrong | ComplyAdvantage | Executive Director, FCC Strategy | iain.armstrong@complyadvantage.com | London | Other | | Oliver`

---

### Tab 3 - Aylin's Priority Intro Requests (lines 138-170, 33 rows)

**Column mapping (4 columns):**
| Col | Header | Maps to |
|-----|--------|---------|
| 1 | Organization | `target_company_raw` |
| 2 | Job Title | `target_title_raw` (use to narrow multi-person match) |
| 3 | Request Meeting | `elliptic_owner` (= "Aylin Zanier" for all 33) |
| 4 | Reason for introduction. | `intro_reason_raw` (keep for context; no direct schema field yet) |

**Sample rows (first 3):**
1. `Amundi | Portfolio Manager | Aylin Zanier | Europe's largest asset manager ($2T AUM) — MiCA and tokenized fund compliance needs...`
2. `Avicenne Studio | CEO | Aylin Zanier | French crypto/digital studio — track.`
3. `AXA | Project manager | Aylin Zanier | Europe's largest insurer — evaluating digital asset products...`

**Last row (line 170):**
`Vancelian | Legal Counsel | Aylin Zanier | Digital asset legal advisory — potential channel partner for Elliptic referrals.`

---

### Tabs 4 / 5 / 5b / 6 - ICP Intelligence (lines 763-1268, combined)

**Column mapping (6-7 columns):**
| Col | Header | Maps to |
|-----|--------|---------|
| 1 | Company | `target_company_raw` |
| 2 | ICP Segment | `icp_segment` (e.g. "Bank / FI", "CEX", "Crypto Native / DeFi") |
| 3 | HQ / Location | `hq_location` |
| 4 | Title(s) from List | `target_titles_raw` (multi-value, comma-separated; pick first or keep all) |
| 5 | Priority Action | `tier_label` (e.g. "Tier 1 — institutional staking", "Tier 3") |
| 6 | Why Meet? | `why_meet_raw` (rich rationale; keep for intro message generation) |
| 7 | (owner col, present in Tab 4/5 only) | `elliptic_owner` ("Ylli", "Oliver", "Simone or James?", "James?", blank) |

**Note on Tab 6:** This table has only 6 columns (no owner col); treat owner as blank/unassigned.

**Sample rows from Tab 5 (lines 765-767):**
1. `LBBW | Bank / FI | Stuttgart, Germany | Product manager | Tier 2 — German Landesbank digital products | Germany's largest Landesbank... | Ylli`
2. `Maerki Baumann | Bank / FI | Zurich, Switzerland | Crypto Lead | Tier 2 — Swiss private bank crypto | Swiss private bank with live crypto offering... | Ylli`
3. `Qivalis | Bank / FI | Amsterdam, Netherlands | CFO | Tier 1 — 37-bank European stablecoin consortium | 37-bank European stablecoin consortium... | Simone or James?`

**Last row of Tab 6 (line 1268):**
`SwissBorg | CEX / Wealth App | Lausanne, Switzerland | Senior RM | Tier 2 — Swiss crypto wealth management | Swiss crypto wealth management platform (€1B+ AUM)...`

---

## 3. EDGE CASES WORTH FLAGGING

### Owner value variants
- Tab 3 owner is **"Aylin Zanier"** (full name), not "Aylin". The ingest script must match this to the `aylin.zanier@elliptic.co` attendee record.
- Tab 4/5 owner for Ylli is exactly **"Ylli"** (no surname) - matches `ylli@elliptic.co` (Ylli Vllasolli per Luma RSVP).
- Two rows have owner **"Simone or James?"** (Qivalis, lines 767 and 836) - ambiguous. Script should flag and not assign.
- Two rows have owner **"James?"** (UBS, lines 768 and 841) - uncertain. Script should flag and not assign.
- One row (European Blockchain Convention, line 1122) has **"Oliver"** as owner in the long-tail NO_HEADER table; this is the only Oliver-tagged row in that section.

### Companies duplicated across tabs
The following companies appear in BOTH Aylin's Tab 3 AND the ICP intelligence tabs (4/5):
- **Kiln** - Aylin (lines 160-161) AND appears in Tab 5b (line 916) assigned to Ylli
- **Morpho** - Aylin (line 165) AND Tab 5b (line 1340) unassigned
- **Meria** - Aylin (line 164) AND Tab 5b (line 1155) unassigned
- **Clearstream Banking Luxembourg SA** - Aylin (line 149) AND Tab 5b (line 856) unassigned
- **Forvis Mazars Group** - Aylin (line 156) AND Tab 5b (line 1200) unassigned
- **R3** - Aylin (line 168) AND Tab 5b (line 1367) unassigned
- **lyzi** - Aylin (line 163) AND Tab 5b (line 1153) unassigned
- **DeFi AM** - Aylin (line 153) AND Tab 5b (line 1333) unassigned

**Resolution:** Aylin's explicit assignment (Tab 3) should win. Keep both records in the intro_requests table but flag the ICP duplicate.

### Companies duplicated WITHIN a single tab
- **Bpifrance** appears **twice in Aylin's list** (lines 144-145): once with "Investment Director" and once with "Financial Analyst". Two different people at the same company - both are valid intro targets. Script should create two distinct intro_request rows.
- **Byzantine Fi** (line 146) and **Byzantine Finance** (line 147) - same company, different name spellings. Both are for "Associate". Script should dedup on fuzzy company name match or flag as possible duplicate.
- **Kiln** (lines 160-161) - "VP Special Projects" and "CEO" - two people, both valid.

### Tab 4 vs Tab 5 overlap
Tab 4 (lines 763-794) is a subset of Tab 5 (lines 806-896). **Every row in Tab 4 reappears in Tab 5 with identical data.** The ingest script must deduplicate by (company + owner) when combining these two tabs, or simply ingest Tab 5 as canonical and ignore Tab 4.

### Title fields that are multi-value
In the ICP intelligence tabs, the "Title(s) from List" column frequently contains multiple titles, e.g.:
- `CEO, Co-Founder`
- `MD Institutional Business x2, Business Operations, CRO`
- `Head of Trading, CEO, Board Member, BD, Partnerships, Finance`
- `CIO Franklin Crypto, DA Partnership Associate, SVP`

These represent multiple people at the same company. The script can either store the raw string as-is (for the matchmaker to resolve) or split on comma and create one row per person. **Recommendation: store raw string + expose a parsed array field.**

### Ambiguous / junk entries in the full attendee tail (lines 171-761)
The blank-owner rows in Tab 3 include:
- `Baguette croissant fromage | Business owner` (line 263) - clearly a joke/test entry
- `Close protection, Security/ Stani | Close protection security/ Stani` (line 360) - event security person
- `Freelance | Photography` (line 483) - individual freelancer
- `Founder | CEO` (line 476) - company name is literally "Founder"
- `None | Security Engineer (electronic)` (line 701)
- `Electric Bank Developer and blockchain Master archive | All chain controller` (line 429)

These are in the attendee-tail section (lines 171-761) which is **not being ingested** as priority intros anyway, but worth noting if that section is later used for reference matching.

### Tier 1 competitors flagged in ICP list
Three rows are explicitly marked as competitors (lines 1389-1391):
- **Crystal Intelligence** - "⚠️ COMPETITOR"
- **Scorechain** - "⚠️ COMPETITOR"
- **TRM Labs** - "⚠️ COMPETITOR"

These are in the ICP intelligence list with "attend to map their strategy" notes. The ingest script should either skip these or tag them with `is_competitor = true`.

---

## 4. ELLIPTIC STAFF IN LUMA RSVP (Tab 2)

Searched all lines 52-134 for `@elliptic.co`:

| Name | Email | Role | Luma Line |
|------|-------|------|-----------|
| Aylin Zanier | aylin.zanier@elliptic.co | Business Development | 85 |
| Ylli V (Ylli Vllasolli) | ylli@elliptic.co | Senior Sales Exec | 80 |

**No oliver@elliptic.co found anywhere in the file.** Oliver's rows in Tab 1 and Tab 4a use only the first name "Oliver" as the owner value. There is no Luma RSVP entry for Oliver - he may not be attending the event, or registered separately.

Other Elliptic staff to check: James Smith (Co-Founder & CSO, line 1442 in the speaker list) is confirmed as a speaker but does NOT have an @elliptic.co email in the Luma RSVP data (he is listed in the speakers tab without an email column).

---

## 5. LINE RANGE QUICK REFERENCE

| Lines | Content | Ingest? |
|-------|---------|---------|
| 1-50 | Meeting Log (CRM tab) - 3 real rows | YES - Tab 1 |
| 51 | Blank separator | - |
| 52-134 | Luma RSVP guest list | NO (use for attendee matching only) |
| 135 | Blank separator | - |
| 136-170 | Aylin's 33 priority intro requests (with owner + reason) | YES - Tab 3 |
| 171-761 | Full PoT attendee tail (no owner, no reason) | SKIP for intros |
| 762 | Blank separator | - |
| 763-794 | Ylli's ICP list v1 (31 rows, 6+1 cols) | INGEST but defer to Tab 5 |
| 795 | Blank separator | - |
| 796-804 | NO_HEADER continuation - Oliver's ICP rows (7 rows) | YES - Tab 4a |
| 805 | Blank separator | - |
| 806-896 | Ylli's ICP list v2 - canonical (90 rows) | YES - Tab 5 |
| 897 | Blank separator | - |
| 898-1255 | NO_HEADER ICP continuation - all blank owner (356 rows) | YES - Tab 5b |
| 1256 | Blank separator | - |
| 1257-1268 | Malformed table - Ledger row as header + 10 more rows | YES - Tab 6 |
| 1269-1392 | More ICP rows in Tab 6 continuation (no header, 6 cols) | YES - Tab 6 cont. |
| 1393 | Blank separator | - |
| 1394-1539 | Speakers / VIP list (4 cols, 145 rows) | NO |
| 1540-1554 | Partners grid (unstructured) | NO |
