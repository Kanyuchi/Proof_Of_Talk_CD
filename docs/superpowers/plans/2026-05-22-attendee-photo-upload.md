# Attendee Photo Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any attendee upload a profile photo from their device on both the logged-in Profile page and the no-login magic-link page.

**Architecture:** Browser center-crops + downscales the chosen image to a 512×512 JPEG on a `<canvas>`, then POSTs the blob (multipart) to FastAPI. A shared backend service validates type/size and uploads to a public Supabase Storage bucket (`avatars`) with the service-role key, then sets `attendee.photo_url`. Two thin endpoints (JWT and magic-token) reuse the service.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx, Supabase Storage REST; React + TypeScript, Vite, React Query; pytest.

**Spec:** `docs/superpowers/specs/2026-05-22-attendee-photo-upload-design.md`

---

## File Structure

- Create `backend/app/services/avatars.py` — validation + Supabase Storage upload (one responsibility: bytes in → public URL out).
- Modify `backend/app/api/routes/matches.py` — add `POST /m/{token}/photo`.
- Modify `backend/app/api/routes/auth.py` — add `POST /profile/photo`.
- Create `backend/tests/test_avatars.py` — service + endpoint tests.
- Create `frontend/src/utils/cropImage.ts` — canvas center-crop/downscale helper.
- Create `frontend/src/components/PhotoUpload.tsx` — shared upload UI.
- Modify `frontend/src/api/client.ts` — two upload functions.
- Modify `frontend/src/pages/Profile.tsx` — mount `PhotoUpload` (authenticated).
- Modify `frontend/src/pages/MagicMatches.tsx` — mount `PhotoUpload` (magic-link).

---

## Task 0: Provision the Supabase Storage bucket (setup, no code)

**Files:** none (infrastructure).

- [ ] **Step 1: Create the public `avatars` bucket**

Via Supabase MCP `execute_sql` (or the dashboard → Storage → New bucket):

```sql
insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true)
on conflict (id) do nothing;
```

- [ ] **Step 2: Verify it exists and is public**

```sql
select id, name, public from storage.buckets where id = 'avatars';
```

Expected: one row, `public = true`. No RLS write policy is needed because all writes go through the backend service-role key (which bypasses RLS). Public read is provided by `public = true`.

---

## Task 1: Backend avatar service — validation

**Files:**
- Create: `backend/app/services/avatars.py`
- Test: `backend/tests/test_avatars.py`

- [ ] **Step 1: Write the failing tests for validation**

```python
# backend/tests/test_avatars.py
import pytest
from app.services import avatars


def test_validate_rejects_non_image_content_type():
    with pytest.raises(avatars.AvatarError) as exc:
        avatars.validate_upload(b"hello", "application/pdf")
    assert "type" in str(exc.value).lower()


def test_validate_rejects_oversize():
    big = b"x" * (avatars.MAX_BYTES + 1)
    with pytest.raises(avatars.AvatarError) as exc:
        avatars.validate_upload(big, "image/jpeg")
    assert "large" in str(exc.value).lower() or "size" in str(exc.value).lower()


def test_validate_rejects_empty():
    with pytest.raises(avatars.AvatarError):
        avatars.validate_upload(b"", "image/jpeg")


def test_validate_accepts_png_jpeg_webp():
    for ct in ("image/jpeg", "image/png", "image/webp"):
        avatars.validate_upload(b"some-bytes", ct)  # no raise
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_avatars.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.avatars` / `AttributeError`.

- [ ] **Step 3: Implement validation**

```python
# backend/app/services/avatars.py
"""Profile-photo upload: validate an image and store it in the Supabase
Storage `avatars` bucket via the service-role key. Returns a public URL.

The browser pre-shrinks images to a 512x512 JPEG, but never trust the client:
content-type and size are re-checked here before anything is stored.
"""
from __future__ import annotations

import time

import httpx

from app.core.config import get_settings

BUCKET = "avatars"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2 MB hard cap (post client-shrink)
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class AvatarError(Exception):
    """Raised on invalid upload (bad type / size) or a storage failure."""


def validate_upload(data: bytes, content_type: str) -> None:
    if content_type not in ALLOWED_TYPES:
        raise AvatarError(f"Unsupported image type: {content_type!r}")
    if not data:
        raise AvatarError("Empty file")
    if len(data) > MAX_BYTES:
        raise AvatarError("File too large (max 2 MB)")
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_avatars.py -v`
Expected: the 4 validation tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/avatars.py backend/tests/test_avatars.py
git commit -m "feat(avatars): image validation for profile-photo uploads"
```

---

## Task 2: Backend avatar service — upload to Supabase Storage

**Files:**
- Modify: `backend/app/services/avatars.py`
- Test: `backend/tests/test_avatars.py`

- [ ] **Step 1: Write the failing test (httpx mocked)**

```python
# add to backend/tests/test_avatars.py
def test_upload_avatar_puts_bytes_and_returns_public_url(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200
        text = ""
        def raise_for_status(self): pass

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, headers=None, content=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["content"] = content
            return FakeResp()

    monkeypatch.setattr(avatars.httpx, "Client", FakeClient)

    url = avatars.upload_avatar("att-123", b"abc", "image/png")

    assert "/storage/v1/object/avatars/att-123.png" in captured["url"]
    assert captured["headers"]["x-upsert"] == "true"
    assert captured["headers"]["Content-Type"] == "image/png"
    assert captured["content"] == b"abc"
    # public URL with cache-buster
    assert "/storage/v1/object/public/avatars/att-123.png?v=" in url


def test_upload_avatar_raises_on_storage_error(monkeypatch):
    class FakeResp:
        status_code = 400
        text = "bad"
        def raise_for_status(self):
            raise httpx_err()
    import httpx as _httpx
    def httpx_err():
        return _httpx.HTTPStatusError("400", request=None, response=None)

    class FakeClient:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, *a, **k): return FakeResp()

    monkeypatch.setattr(avatars.httpx, "Client", FakeClient)
    with pytest.raises(avatars.AvatarError):
        avatars.upload_avatar("att-9", b"abc", "image/jpeg")
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_avatars.py -k upload -v`
Expected: FAIL — `upload_avatar` not defined.

- [ ] **Step 3: Implement the upload**

```python
# append to backend/app/services/avatars.py
def upload_avatar(attendee_id: str, data: bytes, content_type: str) -> str:
    """Validate + store the image; return a public URL with a cache-buster.

    Deterministic key `{attendee_id}.{ext}` so a re-upload overwrites in place
    (x-upsert). The `?v=` suffix forces clients/CDN to refetch after a replace.
    """
    validate_upload(data, content_type)
    settings = get_settings()
    base = settings.SUPABASE_URL.rstrip("/")
    key = f"{attendee_id}.{EXT[content_type]}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{base}/storage/v1/object/{BUCKET}/{key}",
                headers=headers,
                content=data,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AvatarError(f"Storage upload failed: {exc}") from exc
    return f"{base}/storage/v1/object/public/{BUCKET}/{key}?v={int(time.time())}"
```

Note: confirm `Settings` exposes `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `backend/app/core/config.py`. They are used by ingestion scripts already; if the FastAPI `Settings` model lacks them, add both as `str` fields (env-driven) in `config.py` in this step.

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_avatars.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/avatars.py backend/tests/test_avatars.py backend/app/core/config.py
git commit -m "feat(avatars): upload to Supabase Storage, return public URL"
```

---

## Task 3: Magic-link photo endpoint

**Files:**
- Modify: `backend/app/api/routes/matches.py` (add route near the existing `PATCH /m/{token}/profile`)
- Test: `backend/tests/test_avatars.py`

- [ ] **Step 1: Read the existing magic-link profile route**

Open `backend/app/api/routes/matches.py`, find the `@router.patch("/m/{token}/profile")` handler and the helper it uses to resolve an attendee by `magic_access_token` (a `select(Attendee).where(Attendee.magic_access_token == token)`). The new route mirrors that resolution and the router's prefix (`/matches`).

- [ ] **Step 2: Write the failing endpoint tests**

```python
# add to backend/tests/test_avatars.py
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_magic_photo_sets_url_for_token_attendee(monkeypatch, seed_attendee):
    # seed_attendee fixture: an Attendee row with a known magic_access_token.
    monkeypatch.setattr(
        "app.api.routes.matches.upload_avatar",
        lambda aid, data, ct: "https://example/public/avatars/x.jpg?v=1",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post(
            f"/api/v1/matches/m/{seed_attendee.magic_access_token}/photo",
            files={"file": ("a.jpg", b"abc", "image/jpeg")},
        )
    assert r.status_code == 200
    assert r.json()["photo_url"].startswith("https://example/")


@pytest.mark.asyncio
async def test_magic_photo_404_on_bad_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post(
            "/api/v1/matches/m/not-a-real-token/photo",
            files={"file": ("a.jpg", b"abc", "image/jpeg")},
        )
    assert r.status_code == 404
```

If no `seed_attendee` fixture exists in `backend/tests/conftest.py`, add one that inserts an `Attendee` with `magic_access_token="tok_test_123"` into the test DB session and yields it. Match the existing test fixtures' DB-session pattern in `conftest.py`.

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_avatars.py -k magic_photo -v`
Expected: FAIL — route returns 404/405 for the valid-token case (route not defined yet).

- [ ] **Step 4: Implement the route**

```python
# in backend/app/api/routes/matches.py
from fastapi import UploadFile, File, HTTPException
from app.services.avatars import upload_avatar, AvatarError

@router.post("/m/{token}/photo")
async def upload_photo_via_magic_link(
    token: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Attendee).where(Attendee.magic_access_token == token)
    )
    attendee = result.scalar_one_or_none()
    if not attendee:
        raise HTTPException(status_code=404, detail="Invalid link")
    data = await file.read()
    try:
        url = upload_avatar(str(attendee.id), data, file.content_type or "")
    except AvatarError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    attendee.photo_url = url
    await db.commit()
    return {"photo_url": url}
```

Use the same `select`, `Attendee`, `get_db`, and `AsyncSession` imports the file already has; only add `UploadFile/File/HTTPException` and the `avatars` imports if missing.

- [ ] **Step 5: Run to verify pass**

Run: `pytest tests/test_avatars.py -k magic_photo -v`
Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/matches.py backend/tests/test_avatars.py backend/tests/conftest.py
git commit -m "feat(avatars): magic-link photo upload endpoint"
```

---

## Task 4: Authenticated photo endpoint

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_avatars.py`

- [ ] **Step 1: Read the existing auth profile route**

In `backend/app/api/routes/auth.py`, find the authenticated profile handler (the one near line 257 that lists allowed fields incl. `photo_url`) to copy its current-user dependency (e.g. `Depends(get_current_user)`) and how it loads the user's `Attendee`.

- [ ] **Step 2: Write the failing test**

```python
# add to backend/tests/test_avatars.py
@pytest.mark.asyncio
async def test_auth_photo_requires_jwt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post(
            "/api/v1/auth/profile/photo",
            files={"file": ("a.jpg", b"abc", "image/jpeg")},
        )
    assert r.status_code in (401, 403)
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_avatars.py -k auth_photo -v`
Expected: FAIL — route not defined (404).

- [ ] **Step 4: Implement the route**

```python
# in backend/app/api/routes/auth.py
from fastapi import UploadFile, File, HTTPException
from app.services.avatars import upload_avatar, AvatarError

@router.post("/profile/photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Attendee).where(Attendee.id == current_user.attendee_id)
    )
    attendee = result.scalar_one_or_none()
    if not attendee:
        raise HTTPException(status_code=404, detail="No attendee profile linked")
    data = await file.read()
    try:
        url = upload_avatar(str(attendee.id), data, file.content_type or "")
    except AvatarError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    attendee.photo_url = url
    await db.commit()
    return {"photo_url": url}
```

Match the file's existing imports/dependency names (`get_current_user`, `get_db`, `Attendee`, `select`, `AsyncSession`). If the user→attendee link uses a different attribute than `current_user.attendee_id`, use the one the existing profile handler uses.

- [ ] **Step 5: Run to verify pass + full suite**

Run: `pytest tests/test_avatars.py -v && pytest -q`
Expected: new tests PASS; no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/auth.py backend/tests/test_avatars.py
git commit -m "feat(avatars): authenticated profile photo upload endpoint"
```

---

## Task 5: Frontend canvas crop/downscale helper

**Files:**
- Create: `frontend/src/utils/cropImage.ts`

- [ ] **Step 1: Implement the helper**

```typescript
// frontend/src/utils/cropImage.ts
// Center-crop an image File to a square and downscale to 512x512 JPEG.
// Returns a Blob ready for multipart upload. Throws on a non-image file.
const TARGET = 512;

export async function cropImageToSquareJpeg(file: File): Promise<Blob> {
  if (!file.type.startsWith("image/")) {
    throw new Error("Please choose an image file.");
  }
  const bitmap = await createImageBitmap(file);
  const side = Math.min(bitmap.width, bitmap.height);
  const sx = (bitmap.width - side) / 2;
  const sy = (bitmap.height - side) / 2;

  const canvas = document.createElement("canvas");
  canvas.width = TARGET;
  canvas.height = TARGET;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not process image.");
  ctx.drawImage(bitmap, sx, sy, side, side, 0, 0, TARGET, TARGET);

  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Could not process image."))),
      "image/jpeg",
      0.85
    );
  });
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/cropImage.ts
git commit -m "feat(photo): canvas center-crop + downscale helper"
```

---

## Task 6: client.ts upload functions

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Read the file**

Open `frontend/src/api/client.ts` to copy the existing axios instance name (e.g. `api`/`client`) and base-URL convention (routes are under `/api/v1`).

- [ ] **Step 2: Add the two functions**

```typescript
// frontend/src/api/client.ts  (use the existing axios instance, shown here as `api`)
export async function uploadProfilePhoto(blob: Blob): Promise<{ photo_url: string }> {
  const form = new FormData();
  form.append("file", blob, "photo.jpg");
  const { data } = await api.post("/auth/profile/photo", form);
  return data;
}

export async function uploadPhotoViaMagicLink(
  token: string,
  blob: Blob
): Promise<{ photo_url: string }> {
  const form = new FormData();
  form.append("file", blob, "photo.jpg");
  const { data } = await api.post(`/matches/m/${token}/photo`, form);
  return data;
}
```

Do not set `Content-Type` manually — the browser sets the multipart boundary. If the axios instance has a default JSON `Content-Type`, pass `{ headers: { "Content-Type": "multipart/form-data" } }` so axios overrides it with the boundary, or use a per-call config that deletes the default.

- [ ] **Step 3: Type-check**

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(photo): client upload functions (auth + magic-link)"
```

---

## Task 7: PhotoUpload shared component

**Files:**
- Create: `frontend/src/components/PhotoUpload.tsx`

- [ ] **Step 1: Implement the component**

```tsx
// frontend/src/components/PhotoUpload.tsx
import { useRef, useState } from "react";
import { Camera } from "lucide-react";
import { cropImageToSquareJpeg } from "../utils/cropImage";

type Props = {
  /** Uploads the processed blob; resolves to the new public photo URL. */
  uploadFn: (blob: Blob) => Promise<{ photo_url: string }>;
  /** Called with the new URL on success (e.g. to refresh cache/UI). */
  onUploaded?: (url: string) => void;
};

type State = "idle" | "processing" | "uploading" | "success" | "error";

export default function PhotoUpload({ uploadFn, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<State>("idle");
  const [error, setError] = useState<string>("");

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    setError("");
    try {
      setState("processing");
      const blob = await cropImageToSquareJpeg(file);
      setState("uploading");
      const { photo_url } = await uploadFn(blob);
      setState("success");
      onUploaded?.(photo_url);
    } catch (err: any) {
      setState("error");
      setError(err?.response?.data?.detail || err?.message || "Upload failed.");
    }
  }

  const label =
    state === "processing" ? "Processing…" :
    state === "uploading" ? "Uploading…" :
    state === "success" ? "Photo updated" : "Upload / change photo";

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={state === "processing" || state === "uploading"}
        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 hover:text-white hover:border-[#E76315]/50 transition-all disabled:opacity-50"
      >
        <Camera className="w-4 h-4" />
        {label}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFile}
      />
      {state === "error" && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PhotoUpload.tsx
git commit -m "feat(photo): shared PhotoUpload component"
```

---

## Task 8: Mount on the Profile page (authenticated)

**Files:**
- Modify: `frontend/src/pages/Profile.tsx` (header block around the `AttendeeAvatar`, ~lines 118-138)

- [ ] **Step 1: Wire it in**

Add the imports and place `PhotoUpload` next to the avatar in the header. Use React Query's `queryClient.invalidateQueries` for the attendee/profile query key the page already uses so the avatar refreshes.

```tsx
import PhotoUpload from "../components/PhotoUpload";
import { uploadProfilePhoto } from "../api/client";
// inside the component, near other hooks:
const queryClient = useQueryClient();
```

```tsx
{/* in the header, beside <AttendeeAvatar .../> */}
<div className="flex flex-col gap-2">
  <AttendeeAvatar attendee={attendee} size="lg" />
  <PhotoUpload
    uploadFn={uploadProfilePhoto}
    onUploaded={() => queryClient.invalidateQueries()}
  />
</div>
```

If the page already imports `useQueryClient` from `@tanstack/react-query`, reuse it; otherwise add the import. Prefer invalidating the specific attendee/me query key the page uses rather than a blanket invalidate.

- [ ] **Step 2: Type-check + build**

Run: `npx tsc --noEmit && npm run build`
Expected: clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Profile.tsx
git commit -m "feat(photo): photo upload on Profile page"
```

---

## Task 9: Mount on the magic-link page

**Files:**
- Modify: `frontend/src/pages/MagicMatches.tsx` (the enrichment card block, ~lines 209+)

- [ ] **Step 1: Wire it in**

Add `PhotoUpload` inside the enrichment card, bound to the magic token. Invalidate the magic-link attendee/matches query so the avatar updates.

```tsx
import PhotoUpload from "../components/PhotoUpload";
import { uploadPhotoViaMagicLink } from "../api/client";
```

```tsx
{/* inside the enrichment card */}
<div className="space-y-1">
  <label className="text-xs text-white/50">Profile photo</label>
  <PhotoUpload
    uploadFn={(blob) => uploadPhotoViaMagicLink(token!, blob)}
    onUploaded={() => queryClient.invalidateQueries()}
  />
</div>
```

Reuse the page's existing `queryClient` (or add `const queryClient = useQueryClient();`). `token` is the route param the page already reads.

- [ ] **Step 2: Type-check + build**

Run: `npx tsc --noEmit && npm run build`
Expected: clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/MagicMatches.tsx
git commit -m "feat(photo): photo upload on magic-link page"
```

---

## Task 10: Manual E2E + docs

**Files:**
- Modify: `session_log.md`, `whats_next.md`, `project_state.md`

- [ ] **Step 1: Manual E2E (use the `run` skill or `npm run dev` + a local backend)**

1. Log in, open Profile → upload a non-square photo → confirm the avatar updates and the image is square/centered.
2. Open a real `/m/{token}` link → upload from the enrichment card → confirm it appears.
3. Re-upload a different photo on either surface → confirm it replaces (the `?v=` changes).
4. In Supabase Storage, confirm a single `avatars/{attendee_id}.{ext}` object exists per attendee.
5. Try a non-image file → confirm a friendly error, no upload.

- [ ] **Step 2: Update living docs**

Append a dated `session_log.md` entry; move the photo-upload item from Soon to Done in `whats_next.md`; note the new capability + `avatars` bucket in `project_state.md` (What's Working + Infrastructure).

- [ ] **Step 3: Commit + push**

```bash
git add session_log.md whats_next.md project_state.md
git commit -m "docs: attendee photo upload shipped"
git push origin main
```

- [ ] **Step 4: Verify deploy**

Railway auto-deploys backend; Netlify auto-deploys frontend. After deploy, repeat the magic-link upload once on `https://meet.proofoftalk.io` to confirm prod works end-to-end.

---

## Self-Review

**Spec coverage:**
- Storage bucket + deterministic key + cache-buster → Tasks 0, 2. ✓
- Service with validation + Supabase upload → Tasks 1, 2. ✓
- Magic-link endpoint (token-scoped, 404 on bad token) → Task 3. ✓
- Authenticated endpoint (JWT required) → Task 4. ✓
- Client crop/downscale to 512² JPEG → Task 5. ✓
- Shared PhotoUpload component (states) → Task 7. ✓
- Both surfaces wired → Tasks 8, 9. ✓
- No re-embed on photo change → endpoints set `photo_url` only, no embedding call. ✓
- Security: service-role server-side, public-read bucket, server-side validation, token scoping → Tasks 0-4. ✓
- Testing: validator + endpoints + manual E2E → Tasks 1-4, 10. ✓
- Rate-limiting: noted in spec. **Added note:** if `backend/app/utils` exposes a rate-limit dependency (as used by `/auth/forgot-password`), apply it to both new endpoints in Tasks 3-4 (same `Depends(...)` pattern); if not trivially reusable, defer and track in whats_next — do not block the feature.

**Placeholder scan:** No TBD/TODO; every code step has real code. ✓

**Type consistency:** `upload_avatar(attendee_id, data, content_type)` signature is identical across Tasks 2-4. `AvatarError` raised in service, caught in both endpoints. `cropImageToSquareJpeg` / `uploadProfilePhoto` / `uploadPhotoViaMagicLink` names consistent across Tasks 5-9. Endpoint return shape `{photo_url}` matches client function return types and `onUploaded` usage. ✓
