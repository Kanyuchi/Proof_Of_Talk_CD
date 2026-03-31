# Runa × POT Matchmaker — Integration API Specification

**For:** Swerve (Runa/Extasy developer)
**From:** Kanyuchi (POT Matchmaker developer)
**Date:** March 31, 2026
**Status:** Live — endpoints deployed and ready for integration

---

## 1. Overview

The POT Matchmaker is an AI-powered matchmaking engine for Proof of Talk 2026. It matches attendees based on complementary needs, deal-readiness, and non-obvious connections.

**Goal:** Allow Runa ticket buyers to seamlessly access their matchmaker dashboard from within Runa — no separate registration or login required.

**How it works:** Every attendee in our system has a unique **magic link** — a private URL that gives them direct access to their personal matches dashboard. Runa calls our API with the customer's email, gets back their magic link URL, and embeds it as a button or redirect.

```
Customer buys ticket on Runa
        ↓
Customer clicks "View My Matches" in Runa
        ↓
Runa calls:  GET /api/v1/integration/magic-link?email=jane@example.com
        ↓
We respond:  { "magic_link_url": "https://meet.proofoftalk.io/m/abc123..." }
        ↓
Runa redirects customer to that URL
        ↓
Customer lands in their personal matchmaker dashboard
(no login, no password — the magic link IS the authentication)
```

---

## 2. Base URL

```
Staging (use now):   http://3.239.218.239/api/v1
Production (once DNS is fixed):  https://meet.proofoftalk.io/api/v1
```

> **Note:** The `meet.proofoftalk.io` domain is currently down — the CNAME record needs to be re-added (see Section 12 below). In the meantime, build and test against the staging URL. When the DNS is fixed, the only change is swapping the base URL — everything else stays identical.

---

## 3. Authentication

All integration endpoints are protected by an **API key** sent via HTTP header.

```
X-API-Key: your-secret-api-key-here
```

- One key per integration partner (Runa gets one key)
- Key will be shared securely (not via email)
- All production requests must use HTTPS
- The key only grants access to `/api/v1/integration/*` endpoints — not to any other matchmaker endpoints

**Error if missing or invalid:**
```json
HTTP 401
{ "detail": "Missing or invalid API key" }
```

---

## 4. Endpoints

### Endpoint A: Magic Link Lookup *(required — minimum viable integration)*

Look up or create an attendee's matchmaker magic link by email.

```
GET /api/v1/integration/magic-link?email={email}
```

**Headers:**
```
X-API-Key: {api_key}
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | Customer's email address (case-insensitive) |
| `name` | string | No | Customer's full name. Required if attendee doesn't exist yet — we'll create them on-the-fly |
| `ticket_type` | string | No | One of: `delegate`, `sponsor`, `speaker`, `vip`. Default: `delegate` |

**Success Response (200):**
```json
{
  "attendee_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Jane Doe",
  "email": "jane@example.com",
  "magic_link_url": "https://meet.proofoftalk.io/m/Kx7mN2pQ9wR4tY6uI8oP1aS3dF5gH7jL0zX",
  "profile_complete": false,
  "match_count": 8,
  "created_now": false
}
```

| Field | Description |
|-------|-------------|
| `magic_link_url` | The URL to redirect the customer to. This is their personal matchmaker dashboard. |
| `profile_complete` | `true` if they've filled in goals + interests. Useful for showing "Complete Your Profile" vs "View Matches". |
| `match_count` | Number of AI-generated matches. 0 if enrichment is still processing. |
| `created_now` | `true` if we just created this attendee (they weren't in our system yet). Matches will be generated within a few minutes. |

**Error Responses:**

| Status | When | Response |
|--------|------|----------|
| 401 | Missing/invalid API key | `{ "detail": "Missing or invalid API key" }` |
| 404 | Email not found AND no `name` provided | `{ "detail": "Attendee not found. Provide 'name' parameter to create." }` |
| 422 | Invalid email format | `{ "detail": "Invalid email address" }` |

**Behaviour when attendee doesn't exist yet:**

If the email isn't in our system (e.g. ticket just purchased, daily sync hasn't run yet):
- **With `name` provided** → We create the attendee instantly, generate their magic link, and kick off AI enrichment + match generation in the background. Returns `created_now: true`.
- **Without `name`** → Returns 404. You should always pass `name` to avoid this.

**Example — Swerve's implementation:**
```
# When customer clicks "View My Matches" in Runa:
1. Call: GET /api/v1/integration/magic-link?email=jane@example.com&name=Jane+Doe&ticket_type=vip
2. Get back: { "magic_link_url": "https://meet.proofoftalk.io/m/abc123..." }
3. Redirect customer to that URL (window.location.href or new tab)
```

---

### Endpoint B: Ticket Purchased Webhook *(optional — enables real-time sync)*

Push ticket purchase data to us in real-time. This creates the attendee immediately so their matches are ready before they even click "View Matches".

```
POST /api/v1/integration/ticket-purchased
```

**Headers:**
```
X-API-Key: {api_key}
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "ticket_type": "vip pass",
  "ticket_code": "TKT-12345",
  "phone": "+33612345678",
  "country": "FRA",
  "city": "Paris",
  "paid_amount": "2500.00",
  "voucher_code": "EARLYBIRD",
  "extasy_order_id": "ord-abc-123",
  "purchased_at": "2026-04-15T10:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Customer email |
| `first_name` | string | Yes | First name |
| `last_name` | string | Yes | Last name |
| `ticket_type` | string | Yes | Ticket name as it appears in Runa (see mapping below) |
| `ticket_code` | string | No | Unique ticket code |
| `phone` | string | No | Phone number |
| `country` | string | No | ISO 3166-1 alpha-3 country code |
| `city` | string | No | City |
| `paid_amount` | string | No | Amount paid |
| `voucher_code` | string | No | Discount/voucher code used |
| `extasy_order_id` | string | No | Runa/Extasy order ID |
| `purchased_at` | string | No | ISO 8601 timestamp of purchase |

**Ticket Type Mapping:**

We map your ticket names to our internal types:

| Runa Ticket Name | Our Type |
|-----------------|----------|
| `investor pass` | vip |
| `vip pass` | vip |
| `vip black pass` | vip |
| `general pass` | delegate |
| `startup pass` | delegate |
| `startup pass (application based)` | delegate |
| `speaker pass` | speaker |
| `sponsor pass` | sponsor |

> **Question for Swerve:** Are these all the ticket names you use? If you have others, let us know so we can add them.

**Success Response (201 — new attendee):**
```json
{
  "attendee_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "magic_link_url": "https://meet.proofoftalk.io/m/Kx7mN2pQ9wR4tY6uI8oP1aS3dF5gH7jL0zX",
  "status": "created",
  "enrichment_status": "queued"
}
```

**Already Exists Response (200):**
```json
{
  "attendee_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "magic_link_url": "https://meet.proofoftalk.io/m/Kx7mN2pQ9wR4tY6uI8oP1aS3dF5gH7jL0zX",
  "status": "already_exists",
  "enrichment_status": "complete"
}
```

This endpoint is **idempotent** — calling it multiple times for the same email won't create duplicates. Safe to retry on network errors.

---

### Endpoint C: Ticket Cancelled/Refunded *(optional)*

Notify us when a ticket is cancelled or refunded.

```
POST /api/v1/integration/ticket-cancelled
```

**Request Body:**
```json
{
  "email": "jane@example.com",
  "extasy_order_id": "ord-abc-123",
  "reason": "refund"
}
```

**Response (200):**
```json
{
  "attendee_id": "a1b2c3d4-...",
  "status": "deactivated"
}
```

We'll deactivate the attendee (excluded from future match generation, magic link shows a friendly "ticket cancelled" message).

---

### Endpoint D: Attendee Status *(optional — for showing matchmaker status in Runa)*

Check an attendee's matchmaker status. Useful if Runa wants to display "You have 8 matches!" inline.

```
GET /api/v1/integration/attendee-status?email={email}
```

**Response (200):**
```json
{
  "attendee_id": "a1b2c3d4-...",
  "name": "Jane Doe",
  "ticket_type": "vip",
  "has_matches": true,
  "match_count": 8,
  "mutual_matches": 3,
  "profile_complete": false,
  "enriched": true,
  "created_at": "2026-04-15T10:30:00Z"
}
```

| Field | Description |
|-------|-------------|
| `has_matches` | Whether the attendee has any AI-generated matches |
| `match_count` | Total number of matches |
| `mutual_matches` | Matches where both parties accepted — these are "confirmed" connections |
| `profile_complete` | Whether they've filled in goals + interests (affects match quality) |
| `enriched` | Whether our AI pipeline has processed their profile |

**Use case:** Display different CTAs in Runa based on status:
- `profile_complete: false` → "Complete your matchmaker profile"
- `match_count > 0` → "View your 8 matches"
- `mutual_matches > 0` → "3 people want to meet you!"

---

## 5. User Flow Diagrams

### Flow A: With Webhook (Real-Time)

```
┌─────────┐         ┌──────────┐         ┌──────────────┐
│ Customer │         │   Runa   │         │ POT Matchmaker│
└────┬─────┘         └────┬─────┘         └──────┬───────┘
     │  Buy ticket        │                      │
     │───────────────────>│                      │
     │                    │  POST /ticket-purchased
     │                    │─────────────────────>│
     │                    │  { magic_link_url }  │
     │                    │<─────────────────────│
     │                    │                      │──── AI enrichment
     │                    │                      │──── Match generation
     │                    │                      │
     │  Click "View       │                      │
     │  My Matches"       │                      │
     │───────────────────>│                      │
     │                    │  Redirect to         │
     │                    │  magic_link_url      │
     │<───────────────────│                      │
     │                    │                      │
     │  GET /m/{token}    │                      │
     │──────────────────────────────────────────>│
     │              Match dashboard              │
     │<──────────────────────────────────────────│
```

### Flow B: Without Webhook (Using Daily Sync + Magic Link Lookup)

```
┌─────────┐         ┌──────────┐         ┌──────────────┐
│ Customer │         │   Runa   │         │ POT Matchmaker│
└────┬─────┘         └────┬─────┘         └──────┬───────┘
     │  Buy ticket        │                      │
     │───────────────────>│                      │
     │                    │                      │
     │  (daily sync creates attendee at 02:00 UTC)
     │                    │                      │
     │  Click "View       │                      │
     │  My Matches"       │                      │
     │───────────────────>│                      │
     │                    │  GET /magic-link      │
     │                    │  ?email=jane@...      │
     │                    │  &name=Jane+Doe       │
     │                    │─────────────────────>│
     │                    │  { magic_link_url }  │
     │                    │  (creates if needed) │
     │                    │<─────────────────────│
     │                    │  Redirect            │
     │<───────────────────│                      │
     │                    │                      │
     │  GET /m/{token}    │                      │
     │──────────────────────────────────────────>│
     │              Match dashboard              │
     │<──────────────────────────────────────────│
```

**Key difference:** Without the webhook, the attendee might not exist yet when they click "View Matches". The magic link endpoint handles this by creating them on-the-fly (if you pass `name`). Matches will be empty for a few minutes until our AI pipeline runs.

---

## 6. What the Customer Sees

When a customer clicks their magic link, they land on a page that shows:

1. **Their top matches** — AI-ranked by complementarity, deal-readiness, and non-obvious connections
2. **Why each match matters** — AI-generated explanation of why they should meet this person
3. **Action buttons** — "I'd like to meet" / "Maybe later" for each match
4. **Profile enrichment** — if their profile is incomplete, a card prompting them to add goals, interests, LinkedIn

No login, no password. The magic link URL is their key.

---

## 7. Error Response Format

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| 200 | Success |
| 201 | Created (new attendee) |
| 401 | Missing or invalid API key |
| 404 | Attendee not found |
| 422 | Validation error (bad email, missing required fields) |
| 429 | Rate limited — too many requests |
| 500 | Server error |

---

## 8. Rate Limits

| Endpoint | Limit |
|----------|-------|
| Magic Link Lookup (A) | 100 requests/minute |
| Ticket Purchased (B) | 30 requests/minute |
| Ticket Cancelled (C) | 30 requests/minute |
| Attendee Status (D) | 200 requests/minute |

These are generous for 2,500 attendees. If you need higher limits, let us know.

---

## 9. Discussion Points for Swerve

### 9.1 Webhook vs Pull
Do you prefer pushing ticket events to us (Endpoints B/C), or should we continue pulling from the Extasy CSV endpoints daily? The webhook gives real-time magic links but requires you to implement outgoing HTTP calls on ticket purchase. Either way, Endpoint A (magic link lookup) is the minimum you need.

### 9.2 Where does "View Matches" live in Runa?
Suggestions — pick what fits your UI best:
- Post-purchase confirmation page ("Your ticket is confirmed! View your AI matches →")
- Ticket dashboard / "My Tickets" section
- Confirmation email

### 9.3 Redirect vs New Tab vs Iframe
How should the matchmaker open?
- **Redirect** (recommended) — `window.location.href = magic_link_url`
- **New tab** — `window.open(magic_link_url, '_blank')`
- **Iframe** — Not recommended; requires CORS/X-Frame-Options changes on our side

### 9.4 Ticket Type Mapping
Please confirm the ticket names in section 4B match what Runa uses. If you have additional ticket types, send us the list so we can add them to our mapping.

### 9.5 Showing Matchmaker Data in Runa
Do you want to show match count or profile status inline in Runa? If yes, use Endpoint D. If you just need a redirect button, Endpoint A alone is sufficient.

### 9.6 Testing
Ready now:
- Staging API key — will be shared securely by Kanyuchi
- Staging URL: `http://3.239.218.239/api/v1/integration/`
- All 4 endpoints are live and accepting requests
- Test by calling the magic link endpoint with any email + name — it will create an attendee on-the-fly

---

## 10. Implementation Status

| Step | Owner | Status |
|------|-------|--------|
| 1 | **Kanyuchi** | ✅ Done — Endpoints A–D built and deployed to staging (`http://3.239.218.239`) |
| 2 | **Kanyuchi** | ✅ Done — API key generated and ready to share |
| 3 | **Swerve** | **Next** — Review this spec, answer discussion points (Section 9) |
| 4 | **Swerve** | **Next** — Fix `meet.proofoftalk.io` DNS (Section 12) |
| 5 | **Swerve** | **Next** — Integrate Endpoint A into Runa (+ optionally B) |
| 6 | **Both** | Pending — End-to-end test: buy ticket → view matches |
| 7 | **Both** | Pending — Ship to production (swap staging URL for production URL) |

---

## 11. Quick Start for Swerve

**Minimum integration (15 minutes of work):**

1. Get API key from Kanyuchi (will be shared securely)
2. When customer clicks "View Matches":
   ```javascript
   // Use staging URL for now — swap to production once DNS is fixed
   const BASE_URL = "http://3.239.218.239/api/v1";
   // const BASE_URL = "https://meet.proofoftalk.io/api/v1"; // ← production (after DNS fix)

   const response = await fetch(
     `${BASE_URL}/integration/magic-link?email=${customerEmail}&name=${customerName}&ticket_type=${ticketType}`,
     { headers: { "X-API-Key": API_KEY } }
   );
   const { magic_link_url } = await response.json();
   window.location.href = magic_link_url;
   ```
3. Done. Customer lands in their matchmaker dashboard.

---

## 12. DNS Fix Required — meet.proofoftalk.io

The `meet.proofoftalk.io` subdomain is currently down (NXDOMAIN). The CNAME record has been deleted or expired.

**Action needed:** Re-add this DNS record in the `proofoftalk.io` DNS settings:

```
Type:   CNAME
Name:   meet
Value:  pot-matchmaker.netlify.app
```

This should propagate within 5 minutes. Once live:
- The matchmaker frontend will be accessible at `https://meet.proofoftalk.io`
- The API will be accessible at `https://meet.proofoftalk.io/api/v1`
- Magic links will use the `meet.proofoftalk.io` domain
- Swap the `BASE_URL` in your integration code from the staging IP to the production domain

---

**Questions?** Reach out to Kanyuchi.
