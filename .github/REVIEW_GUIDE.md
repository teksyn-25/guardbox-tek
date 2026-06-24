# Code Review Checklist for GuardBox

Required checks for all PRs before merging to `master`.

## General (All PRs)

- [ ] Commit messages are clear — first line under 72 chars, body explains *why*
- [ ] Tests pass — GitHub Actions shows green
- [ ] No secrets committed — `.env`, API keys, tokens not in the diff
- [ ] Documentation updated — if changing user-facing behavior, update README or CLAUDE.md
- [ ] No dead code — no unused imports, commented-out blocks, or orphaned functions

## Authentication

**Files:** `api/auth.py`, `api/middleware.py`, `admin_auth.py`

- [ ] User ID never comes from query params — always extracted from Bearer token or HttpOnly cookie
- [ ] Session tokens are signed — using `itsdangerous`; not plain text or guessable
- [ ] HttpOnly cookie for web UI — JavaScript cannot read the session cookie
- [ ] Bearer token for REST API — Flutter app reads token from response
- [ ] Test covers auth failure — at least one test without token or with invalid token (expect 401)
- [ ] Test covers user isolation — User A cannot access User B's data (expect 404)
- [ ] Logout clears state — session cookie is invalidated
- [ ] No hardcoded secrets — all config from env vars

## Storage

**Files:** `storage/interface.py`, `storage/local.py`

- [ ] Only calls methods defined in `storage/interface.py` — no direct imports of `local.py` outside `storage/`
- [ ] `STORAGE_BACKEND` env var selects implementation — no hardcoded `if self_hosted:` checks
- [ ] Metadata minimization rule followed — new fields justified in CLAUDE.md minimization table
- [ ] Test includes user isolation — one user cannot access another's files
- [ ] Pending vs. saved state enforced — valid state transitions only
- [ ] Test covers error cases — FileNotFoundError, missing file

## CDR

**Files:** `cdr/sanitize.py`

- [ ] Input file never modified in-place — always extract and rebuild fresh
- [ ] Output is always PNG — even if input is JPEG/WebP
- [ ] Magic bytes checked, not extension — actual file type from binary header
- [ ] Metadata stripping is comprehensive — EXIF, XMP, GPS, embedded thumbnails removed
- [ ] Processing in-memory/tmpfs only — original never written to disk
- [ ] Error handling doesn't leak original — errors don't return chunks of original file
- [ ] Test covers malformed input — corrupt or truncated file fails gracefully

## Intake

**Files:** `intake/telegram_bot.py`, `intake/upload.py`

### Telegram Bot
- [ ] File fetched server-to-server — bot calls `getFile` via Telegram API, not through device
- [ ] No original stored — file is streamed through CDR and stored as reconstructed PNG only

### WhatsApp / Flutter Share Handler
- [ ] Bytes streamed directly — Flutter app passes bytes straight to upload endpoint, no intermediate caching
- [ ] File size validated before upload — prevent large file abuse
- [ ] Test covers user isolation — file uploaded by User A goes to User A's pending folder

## API & Middleware

**Files:** `api/auth.py`, `api/files.py`, `api/web.py`, `api/middleware.py`

- [ ] All protected routes use `require_user` dependency
- [ ] Status codes correct — 401 (no auth), 404 (not found or wrong user), 204 (success no body)
- [ ] Error responses don't leak user data — 404 returned whether file is missing or belongs to another user
- [ ] Query params validated — `state=pending|saved` enforced
- [ ] Test covers happy path AND error path

## Web UI & Templates

**Files:** `api/web.py`, `backend/templates/*`, `backend/static/*`

- [ ] No external CDN calls — no Google Fonts, no external JS/CSS
- [ ] Static assets bundled — HTMX, Alpine served locally
- [ ] XSS protection — user-controlled data escaped before rendering
- [ ] HttpOnly cookie never exposed to JavaScript

## Security & Hardening

**Files:** `docker-compose.yml`, `seccomp-profile.json`, `backend/Dockerfile`

- [ ] `cap_drop: ALL` in compose
- [ ] Read-only root filesystem
- [ ] Seccomp profile enforced
- [ ] Non-root user (`guardbox`)
- [ ] `no-new-privileges: true`
- [ ] tmpfs for temp files

## Metadata & Logging

- [ ] No new metadata fields without justification in CLAUDE.md minimization table
- [ ] No timestamps stored
- [ ] No IP addresses logged
- [ ] No user agent logged
- [ ] No Telegram/WhatsApp message IDs stored

## Test Coverage

Every PR must include tests covering:

- [ ] Happy path
- [ ] Auth failure (401)
- [ ] User isolation (404 for wrong user)
- [ ] Error handling (bad input, missing file)

**Test quality:**
- [ ] No storage mocks — use real `LocalStorage` with `pytest tmp_path`
- [ ] Tests are deterministic
- [ ] Test names are descriptive (`test_list_isolates_users` not `test_list`)

## When to Request Changes (Do Not Merge If)

1. Tests fail
2. Any checklist item above is unchecked
3. Metadata rule violated — new fields without CLAUDE.md justification
4. User isolation broken
5. Auth bypassed — any endpoint reachable without valid token
6. Original file returned to client — CDR claims broken
7. No tests added for new code

---

*Last updated: 2026-06-24*
