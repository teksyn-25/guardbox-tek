# GuardBox — Security Audit Scope & Threat Model (v1)

## 1. Context

GuardBox is an open-source (AGPL-3.0), self-hostable tool that protects users from malicious files received via messaging apps (Telegram, WhatsApp). Incoming files are never decoded on the user's device; they are processed server-side inside a hardened sandbox and rebuilt from scratch via Content Disarm & Reconstruction (CDR). The user only ever sees the reconstructed clean copy.

**Stack (v1):** Python (FastAPI + HTMX), CDR via libvips (pyvips), hardened Docker (runc) sandbox, files-on-disk + JSON sidecars (no database). **Planned (v2):** Rust CDR core, micro-VM isolation, S3 + Postgres.

## 2. Assets to protect

- **User device / OS integrity** — the primary asset; file exploits must not reach it.
- **Host/server** — the sandbox must contain a compromised parser.
- **User files** — one user must never reach another's; clean copies served only to the owner.
- **User privacy / metadata** — nothing about the original file or the request is retained.

## 3. Adversary model

- **Primary:** the *sender* of a file — a crafted image designed to exploit a parser, gain code execution, and escape to the host or user device.
- **Secondary:** an authenticated user attempting to reach another user's files; a network attacker.
- **Assumptions:** attacker can submit arbitrary bytes via intake; TLS in transit; the self-hosted operator is trusted.

## 4. Trust boundaries

1. Messaging platform → GuardBox backend (Telegram server-to-server `getFile`; WhatsApp share-sheet upload).
2. **Backend → CDR sandbox** — untrusted bytes cross into the parser here (the critical boundary).
3. **Sandbox → host** — must be one-way containment.
4. Storage → API → user — per-user isolation.

## 5. Threats & current controls (audit focus)

| Threat | Control today | What the auditor should push on |
|---|---|---|
| Malicious file → parser RCE | Decode only via the format-specific loader chosen from verified magic bytes; whitelist reconstruction; hardened sandbox | Can any path reach an unintended loader (SVG/PDF delegates)? Memory safety of libvips usage |
| Decompression bomb | Pixel-count guard checked before re-encode | Does the guard fire before allocation, on every format? |
| Polyglot / format confusion | Magic-byte detection + loader whitelist, no auto-detect | Try to smuggle a second format past the whitelist |
| Container escape after RCE | `cap_drop: ALL`, `no-new-privileges`, read-only rootfs, tmpfs, seccomp, non-root, localhost-bound | ⚠️ **seccomp is a default-allow blocklist, not an allowlist** — primary focus; test escape resistance |
| Cross-user file access | `user_id`-scoped storage paths | IDOR / path traversal to another user's files |
| Metadata leakage | Sidecar limited to defined fields; no IP/UA/timestamps logged | Verify no forbidden field is stored or logged anywhere |
| Auth / session | Password + signed session token + progressive login throttle | ⚠️ **tokens are stateless, non-revocable** — verify signing, expiry, throttle |
| SSRF via intake | Telegram `getFile` is server-to-server; upload streams bytes | Confirm no user-controlled URL fetch |
| XSS / CSRF (web UI) | Server-rendered templates; session cookie httponly/samesite=strict | Template injection; CSRF on mutating routes |

## 6. Known limitations (honest, on the roadmap)

- seccomp is a **default-allow blocklist** → migration to default-deny allowlist is planned (grant milestone M1).
- CDR currently runs **in-process** in the long-lived container → planned ephemeral per-file isolation + micro-VM (M1, M3).
- Session tokens are **stateless/non-revocable** → planned opaque/PASETO tokens (v2).

## 7. Security claims to verify

- "The original is never decoded on the user's device."
- "Structural exploits are removed by construction (CDR), not detection."
- "Nothing about the original file or request is retained (metadata minimization)."
- "Ephemeral, isolated processing. Encrypted in transit and at rest. Zero retention by default."
- *(GuardBox deliberately does NOT claim E2E encryption or zero-click protection — do not test against those.)*

## 8. Out of scope

Messaging-app clients themselves; network-layer DoS; physical access / host-OS hardening beyond the container; social engineering.

## 9. Auditor access

Public source (AGPL-3.0); build/run via `docker-compose up`; configuration via env vars (`.env.template`); contact: **[YOU — your email]**.
