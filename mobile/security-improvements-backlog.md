# Security & Privacy Improvements Backlog

These are real gaps — not theoretical. Pick them up after the Flutter app ships.
Each item is self-contained so they can be done in any order.

---

## High priority (real attack surface)

### 1. HTTP security headers middleware
FastAPI adds no security headers by default. Add a middleware in `backend/app.py`:
- `Strict-Transport-Security: max-age=63072000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer` — without this, browsers leak navigation URLs to sub-resources
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; img-src 'self' blob:; …`
- `Cache-Control: no-store` on all authenticated responses

**File:** `backend/app.py` — one middleware, ~20 lines.

### 2. Rate limiting on auth and upload endpoints
No brute-force or flood protection on:
- `POST /api/auth` (password login)
- `POST /upload` and `POST /api/files/upload`

Add `slowapi` (FastAPI rate-limit library) or handle at the reverse-proxy level (nginx `limit_req`).

### 3. Access log IP stripping
Uvicorn logs every request with the client IP. Those are privacy-sensitive.
Options:
- Already partially done (`logging.getLogger("uvicorn.access").setLevel(logging.WARNING)` in `app.py`)
- Verify no IPs appear in any log output under load
- Add `--no-access-log` flag to the uvicorn startup command in `docker-compose.yml`

---

## Medium priority

### 4. Decompression bomb protection in CDR
A crafted 1 KB PNG can expand to gigabytes when pyvips decodes it.
Add a pixel-count limit after `pyvips.Image.new_from_buffer`:
```python
MAX_PIXELS = 50_000_000  # 50 MP
if image.width * image.height > MAX_PIXELS:
    raise UnsupportedFileType("image too large after decode")
```
**File:** `backend/cdr/sanitize.py`

### 5. Token revocation (v2)
Current itsdangerous tokens are stateless — logging out deletes the cookie but the
token remains valid until expiry if extracted. Fix in v2 when a database is available:
switch to opaque DB tokens or PASETO v4 with a server-side revocation list.
**File:** `backend/api/middleware.py`, `backend/api/auth.py`

### 6. Explicit CORS lockdown
FastAPI with no CORS middleware returns no `Access-Control-Allow-Origin`, which is
correct — but should be made explicit so it can never accidentally be widened:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=[])
```
**File:** `backend/app.py`

---

## Note on cookies

HttpOnly + Secure + SameSite=strict is the correct choice for browser-based sessions.
The alternative (localStorage tokens) is worse — JavaScript and XSS can read localStorage
but cannot read HttpOnly cookies. The session cookie is not a vulnerability; it is the
right tool. What to add is `Cache-Control: no-store` on authenticated responses (item 1).

---

## Effort estimate

| Item | Estimate |
|---|---|
| Security headers middleware | 2–3 h including tests |
| Rate limiting | 3–4 h |
| Access log audit | 1 h |
| Decompression bomb limit | 1 h |
| Token revocation | 1–2 days (needs DB, v2 only) |
| CORS lockdown | 30 min |
