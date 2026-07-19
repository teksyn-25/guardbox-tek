# GuardBox — Status & Roadmap

> **Maturity:** v1 core works and is tested. **Not yet independently security-audited** — a third-party audit is a funded post-Kickstarter milestone. Not for high-risk threat models until then.

**Legend:** ✅ done & tested · 🚧 in progress · ⬜ planned (post-funding)

## Core (v1)

CDR engine ✅ · whitelisted format loaders + magic-byte typing ✅ · decompression-bomb guard ✅ · local storage (files + JSON sidecars) ✅ · Telegram intake ✅ · Web UI (HTMX) ✅ · auth + login throttle ✅ · docker-compose install ✅ · WhatsApp share-sheet (Flutter) 🚧 *v1.1*

## Sandbox & hardening

| Item | Status |
|---|---|
| Non-root · read-only rootfs · no-new-privileges · tmpfs · localhost-bound | ✅ |
| `cap_drop: ALL` | ✅ |
| seccomp profile (escape/exploit syscalls) + CI tests | ✅ |
| seccomp default-allow → default-deny allowlist | ⬜ *interim → planned* |
| AppArmor profile | ⬜ |
| Ephemeral per-file CDR sandbox (`--network none`, `--rm`) | ⬜ |
| Third-party security audit | ⬜ *funded* |

## Isolation trajectory

- **v1 (self-hosted):** ✅ hardened container (runc, shared kernel) — seccomp + cap-drop.
- **v2 (cloud/paid):** ⬜ **microVM per workload (Kata + Firecracker)** — hardware-isolated guest kernel; container hardening becomes defense-in-depth inside the VM.

## v2 / post-funding

Rust CDR core ⬜ · Firecracker isolation ⬜ · cloud storage (S3 + Postgres) ⬜ · mobile apps ⬜ · more formats (PDF…) ⬜
