# Security Model

## Core Principles

1. **Exploit Isolation, Not Detection** — GuardBox uses CDR: decode, extract safe content, rebuild fresh. Exploits hidden in file structure are discarded by construction, not detected.
2. **Metadata Minimization** — Only the minimum metadata required for function is retained. See `CLAUDE.md` for the full minimization table.
3. **Zero Retention by Default** — Files stay in `pending` until the user explicitly saves or deletes them.
4. **Sandboxed Processing** — File parsing runs inside a hardened Docker container: `cap_drop: ALL`, read-only filesystem, tmpfs-only writes, non-root user, custom seccomp profile.

## What GuardBox Protects Against

| Threat | Covered | How |
|---|---|---|
| Malicious file structure exploits | YES | CDR reconstruction discards exploit payloads; parser in sandbox |
| Embedded metadata (EXIF, XMP, GPS) | YES | Stripped during reconstruction |
| Malicious file extensions | YES | Type identified from magic bytes, not filename |
| Zero-day parser bugs | PARTIAL | libvips in hardened container; escape is difficult but not impossible |
| Network sniffing | PARTIAL | HTTPS in transit; Telegram bot is server-to-server (no device involvement) |
| Compromised device OS | NO | Kernel-level access bypasses GuardBox entirely |

## What GuardBox Does NOT Claim

- **End-to-end encryption** — GuardBox must decode the file to sanitise it.
- **Zero-click protection** — GuardBox only enters the path when you forward/share a file.
- **"Never on device" for Telegram** — The original may briefly cache in Telegram's app sandbox during the forward, depending on client version. Outside GuardBox's control.
- **"Never on device" for WhatsApp** — WhatsApp's sandbox holds the file to make it shareable. Only "never in GuardBox's storage" and "never decoded by GuardBox on device" can be claimed.

## Known Limitations (v1 Self-Hosted)

| Limitation | Severity | Impact | Mitigation / Status |
|---|---|---|---|
| libvips parser exploits | Medium | Possible RCE in CDR container | Docker sandbox limits damage; non-root user |
| Decompression bomb | Medium | Crafted file expanding to huge image could exhaust server memory before pixel count is checked | No size limit on decoded pixels yet — fix deferred post v1.0 delivery |
| `FileTooLarge` not caught in intake | Low | Depends on decompression bomb fix; if triggered today falls to generic error handler | Deferred together with bomb fix |
| Brief Telegram sandbox cache | Low | Original briefly in Telegram's private storage | Auto-download must be OFF |
| Single-machine storage | Low | No redundancy | User responsible for host backups |
| HTTP by default | Low | No TLS on localhost | Use Caddy reverse proxy for remote access |

## Hardening Checklist (Self-Hosters)

- [ ] Docker CE is up to date
- [ ] Firewall blocks inbound port 8000 (or use reverse proxy with TLS)
- [ ] `SESSION_SECRET` is 32+ random bytes
- [ ] `BOT_TOKEN` is in `.env` only — never committed
- [ ] Bot is not added to any public groups
- [ ] `SESSION_SECURE_COOKIE=true` when behind HTTPS

## Testing & Validation

| Area | Tests | Notes |
|---|---|---|
| API endpoints (`api/`) | ✅ | Auth, user isolation, state transitions, 404 vs 403 |
| Authentication (`auth.py`) | ✅ | Token validation, expiry, first-run setup |
| Middleware | ✅ | Bearer token and HttpOnly cookie paths |
| Storage (`storage/local.py`) | ✅ | File operations, user boundary enforcement |
| CDR engine (`cdr/sanitize.py`) | ✅ | Format detection, corrupted input, EXIF stripping, output format |
| Telegram intake | ✅ | Bot adapter, file forwarding path |
| Upload intake | ✅ | Share-sheet upload endpoint |
| Container hardening | ✅ | seccomp profile, capability drop, non-root user |

**Total: 165 tests, all passing.**

### Automated scanning on every PR

| Tool | What it checks |
|---|---|
| Bandit | Python SAST — hardcoded secrets, unsafe calls |
| pip-audit | Python dependency CVEs (OSV database) |
| dart pub audit | Flutter dependency advisories (pub.dev) |
| OWASP Dependency-Check | Python dependency CVEs (NVD database) |
| Semgrep | Python + Dart SAST — auth bypasses, injection, OWASP Top 10, secrets |
| CodeQL | Deep Python SAST — inter-procedural analysis, security-extended ruleset |
| MyPy | Type correctness — prevents class of type-confusion bugs |
| Trivy | Container image CVEs |
| Hadolint | Dockerfile best practices |
| Gitleaks | Secret scanning across full git history |
| OpenSSF Scorecard | Overall security posture score (published to securityscorecards.dev) |

### Development process

New code requires TDD: test is written first (and must be seen failing), then implementation. No new code merges without a test that defines the expected behavior.

## Audit History

| Date | Type | Result |
|---|---|---|
| 2026-06-24 | Internal — v1 architecture review | Passed. No critical issues. |

Third-party audit planned after v1.0 release.

## Responsible Disclosure

Do **not** open a public GitHub issue for security vulnerabilities.

Email `guardbox@teksynai.com` with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

We will acknowledge within 48 hours and issue a fix before public disclosure.

## Incident Response

1. Stop the service: `docker compose down`
2. Preserve logs before restarting
3. Email `guardbox@teksynai.com` with logs and timestamps
4. Rotate `SESSION_SECRET` and `BOT_TOKEN` before restarting

---

*Last updated: 2026-06-27*
