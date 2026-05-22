# Attendee Photo Upload — Design Spec

**Date:** 2026-05-22
**Status:** Approved (design), pending implementation plan
**Approach:** A — backend-proxied upload to Supabase Storage, client-side downscale

## Problem

Most attendees have no profile photo. The LinkedIn scraper only captures a photo
when the target's LinkedIn photo is publicly visible (per the `no-photo-means-no-photo`
rule), so a large share of attendees will never get one that way. There is no usable
self-serve path today:

- The main **Profile page has no photo field** (it only *displays* the avatar).
- The **magic-link page** collects LinkedIn/Twitter/goals/target-companies but **not photo**.
- The only existing photo entry is the **Concierge chat offer**, which is **URL-paste only**
  and appears only when `photo_url` happens to be the rotated "next missing field".
- There is **no file storage** anywhere (no Supabase Storage, no Netlify Blobs) — every
  `photo_url` write is a raw URL string.

"Paste an image URL" is unusable for non-technical attendees. We need a real
"upload a photo from your device" path, open to **all** attendees (with or without a
scraped photo), on both the logged-in and magic-link surfaces.

## Decisions (locked)

| Decision | Choice |
|---|---|
| Mechanism | True file upload (device → storage), not URL-paste |
| Surfaces | Both: logged-in Profile page **and** magic-link `/m/{token}` page |
| Storage/processing | Approach A: backend-proxied upload to Supabase Storage; client-side downscale |
| Replace behavior | Anyone can set/replace, including over a scraped photo |

## Architecture

### Storage
- New Supabase Storage bucket **`avatars`**, **public-read**, writes only via the
  backend using the service-role key.
- Deterministic object key **`{attendee_id}.jpg`** → "replace photo" overwrites in
  place (no orphaned objects; covers replacing a scraped photo).
- `attendee.photo_url` = the public object URL plus a `?v={unix_ts}` cache-buster so a
  replaced image displays immediately past CDN/browser cache.

### Backend
- **`app/services/avatars.py`** — `upload_avatar(attendee_id, file_bytes, content_type) -> str`:
  - Validates `content_type ∈ {image/jpeg, image/png, image/webp}` and
    `len(file_bytes) ≤ 2 MB` (server-side; does not trust the client).
  - Uploads to bucket `avatars` key `{attendee_id}.jpg` via Supabase Storage REST
    (`x-upsert: true`) with the service-role key.
  - Returns the public URL with the `?v={unix_ts}` cache-buster already appended
    (single source of truth; callers persist the returned string verbatim).
- **Two thin endpoints** sharing the service:
  - `POST /auth/profile/photo` — JWT auth; resolves the caller's attendee.
  - `POST /matches/m/{token}/photo` — token-scoped; resolves attendee by
    `magic_access_token`; **404** on unknown token; sets only that attendee's photo;
    rate-limited.
  - Both accept multipart `file`, call `upload_avatar`, set `attendee.photo_url`,
    commit, and return `{ "photo_url": "..." }`.
  - **No re-embed** — photo does not affect matching (consistent with the existing
    `chat.py` save-field behavior for `photo_url`).

### Frontend
- **`PhotoUpload.tsx`** (shared component):
  - Renders the current avatar (`AttendeeAvatar`) + an "Upload photo" / "Change photo"
    button wired to a hidden `<input type="file" accept="image/*">`.
  - On select: read the file → `<canvas>` **center-crop to square** → **downscale to
    512×512** → export **JPEG (quality ≈ 0.85)** → `Blob`.
  - POSTs the blob via an injected `uploadFn(blob) => Promise<{photo_url}>` so one
    component serves both surfaces.
  - States: `idle` / `processing` / `uploading` / `success` / `error`
    (wrong type, too big, network failure).
- Wire-in:
  - **Profile.tsx** — replace the static `AttendeeAvatar` in the header with
    `PhotoUpload`, using `uploadProfilePhoto(blob)` (authenticated).
  - **MagicMatches.tsx** — add `PhotoUpload` to the enrichment card, using
    `uploadPhotoViaMagicLink(token, blob)`.
  - **client.ts** — two new API functions.
  - **AttendeeAvatar.tsx** — unchanged; already renders `photo_url`.

## Data flow

pick file → client center-crop + downscale (512² JPEG) → multipart POST →
backend validates type+size → Supabase Storage upsert (`avatars/{attendee_id}.jpg`) →
public URL (+`?v=ts`) → set `attendee.photo_url` → commit → return URL →
frontend updates the avatar (and React Query cache).

## Security

- Service-role key never leaves the backend; bucket is public-**read** only (no public write).
- Magic-link endpoint is strictly scoped to the token's own attendee — a token can only
  set its own photo (consistent with the read access that token already grants to that
  attendee's matches).
- Server-side content-type + size validation (never trust the client crop). Hard size cap.
- Deterministic key avoids storage enumeration growth and auto-overwrites on replace.
- Both endpoints rate-limited (reuse the existing rate-limit util).

## Testing

- **Backend (pytest):** validator rejects non-image content-type and oversize payloads;
  magic-link endpoint sets the correct attendee's `photo_url` and returns 404 on a bad
  token; auth endpoint requires a valid JWT. Supabase Storage upload mocked.
- **Frontend:** the canvas helper produces a square JPEG blob from a non-square input;
  component renders processing / success / error states.
- **Manual E2E (browser):** upload from the logged-in Profile page and from a magic link;
  confirm the photo appears, persists in Supabase Storage, and that a second upload
  overwrites the first.

## Setup step

Provision the `avatars` bucket once (public-read) — via the Supabase MCP or the
dashboard — before the endpoints are exercised.

## Out of scope (YAGNI)

- Drag-to-reposition / zoom crop UI (center-crop only).
- Multiple photos per attendee.
- AI/image moderation.
- Removing the existing Concierge URL-paste offer (left in place).
