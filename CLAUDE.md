# GuardBox

## What this is

A CDR (Content Disarm & Reconstruction) tool for files received via messaging apps.
Files are decoded and rebuilt inside an isolated sandbox — exploits hidden in the
original file's structure are discarded by construction, not detection. GuardBox's
app on the user's device never decodes the original; only the reconstructed clean
copy is displayed. Per-platform claim precision is in the Security Claims section
below.

Open-core, AGPL-3.0 (dual-licensed — commercial license available for enterprise), EU-hosted, built in Stockholm.

---

## Stack

| Layer | v1 (self-hosted) | v2 (cloud / paid) |
|---|---|---|
| Frontend | React (+ Capacitor shell for mobile) | Same |
| Backend language | Python | Python; CDR core migrates to Rust |
| Bot intake | Telegram Bot API (`python-telegram-bot`) | Same |
| Share-sheet intake | Capacitor app (WhatsApp / other apps) | Same |
| CDR engine | Python calling libvips (pyvips) | Rust binary (via PyO3 or standalone) |
| Sandbox runtime | Hardened Docker (runc) | Kata + Firecracker / Cloud-Hypervisor |
| Storage | KVM disk + JSON sidecars, NO database | S3-compatible + Postgres |
| Infrastructure | Bash scripts | Terraform |
| License | AGPL-3.0 | AGPL-3.0 (or commercial license for enterprise) |

### Why Python for v1

The CDR logic is thin glue around C libraries (libvips) that do the real work. The
sandbox contains exploits, not the language. Python gets us to a shippable demo in
weeks; Rust would take months for the same result. The Telegram bot and image library
ecosystems are most mature in Python.

### Why Rust for v2 CDR core

Rust's ownership model prevents the exact class of bugs (buffer overflows,
use-after-free) that file-parser exploits target. Writing the CDR core in Rust means
our own code can't have the memory-corruption bugs we're protecting users against.
Single-binary deployment is also cleaner for self-hosters. Migrate the CDR hot path
to Rust via PyO3 once v1 is shipped and funded.

### Why AGPL-3.0, dual-licensed

Apache 2.0 lets anyone — including large enterprises — use, modify, and deploy the
code commercially without ever paying or contributing back. That's incompatible with
"individuals free, enterprises pay." AGPL-3.0 requires anyone who runs the software
and lets others interact with it over a network to publish their modified source.
Enterprises generally can't accept that obligation internally, so they buy a
commercial license instead. Individuals, researchers, and self-hosters who don't mind
the AGPL terms use the software free, forever, fully open.

**Requirement: a Contributor License Agreement (CLA) on all external contributions.**
Dual-licensing only works if GuardBox Labs holds full rights to relicense the code
commercially. Without a CLA, contributed code stays AGPL-only and can't be sold under
the commercial terms. Set up the CLA before accepting the first external PR.

---



### Portability (see `docs/guardbox-portability-rules.md` for the full version)
- **Same code everywhere.** Only env vars and infrastructure definitions differ.
- **HTTPS / TLS everywhere.** Never plaintext HTTP. Not even in dev if avoidable.
- **No provider lock-in.** No AWS Lambda handlers, no DynamoDB, no proprietary SDKs.
- **No hardcoded URLs, buckets, regions, or credentials.** Everything in env vars.
- **No third-party CDN calls at runtime.** Bundle fonts, scripts, everything. The app
  must run fully offline / air-gapped. No Google Fonts imports.
- **Secrets out of the repo.** Commit `.env.template`, gitignore `.env`.

### Storage (the one deliberate code-level divergence)
- **Self-hosted: NO database.** Files on KVM disk (`pending/{uid}/`, `saved/{uid}/`),
  metadata as JSON sidecars (`{file_id}.json`). Nothing to install or back up.
- **Cloud: ALWAYS a database.** S3-compatible object storage + Postgres.
- **Both behind one interface** (`storage/interface.py`). The rest of the codebase
  imports only the interface — never `local.py` or `cloud.py` directly. Selected by
  `STORAGE_BACKEND=local|cloud` env var at startup.
- **No SQLite "middle ground."** A database is a database. Self-hosters who outgrow
  files-on-disk are ready for the cloud version.

### CDR
- **Never modify the input file. Always extract content and write a fresh file.**
- **Whitelist, never blacklist.** Define what's allowed in the output; drop everything else.
- **Strict file-type identification.** Verify actual type from magic bytes, not extension
  or claimed MIME. Reject mismatches.
- **The parser runs inside the sandbox, always.** The parser IS the attack surface.
- **In-memory processing (tmpfs).** Never write the original to disk, even inside the
  sandbox. In-memory = no traces. Sandbox = containment. Both required.

### Security claims — what we say and don't say

- **Telegram path:** "The original never travels through your device." TRUE
  (server-to-server via the bot). The reconstructed clean copy is what the app
  displays.
- **WhatsApp path:** "The original is never decoded on your device, never saved to
  your gallery, never stored in GuardBox's own storage." TRUE (share-sheet bytes are
  streamed through memory only; WhatsApp's own private sandbox holds the file
  briefly to make it shareable — that part is outside our control).
- **Do NOT claim end-to-end encryption.** GuardBox must read the file to sanitise it.
- **Do NOT claim zero-click protection.** GuardBox enters the path only when the user
  shares a file to it. Say "zero-day protection via CDR reconstruction" instead.
- **Do say:** "Ephemeral, isolated processing. Encrypted in transit and at rest. Zero
  retention by default. Open source. Self-hostable."

#### Telegram path — claim truth table (assumes required user posture configured)

| Claim | True / False | Notes |
|---|---|---|
| "Never saved to the gallery" | ✅ TRUE | With "Save to Gallery" off and the app never writing to the gallery. |
| "Never in Telegram's sandbox on the device" | ⚠️ MOSTLY TRUE — caveat | With auto-download off, Telegram doesn't fetch automatically. The forward action *may* briefly cache the file in Telegram's private app sandbox depending on client version/platform. Invisible to other apps, ephemeral. |
| "Never on the device's disk at all" | ⚠️ MOSTLY TRUE — same caveat | Cannot guarantee absolute "never on disk" across all Telegram client versions. The brief sandbox cache during forward is the exception. |
| "Never decoded by any app on the device" | ✅ TRUE | Telegram passes the file as opaque bytes during a forward; GuardBox's app never sees the original at all. |
| "GuardBox itself never receives the original via the device" | ✅ TRUE | Bot adapter calls `getFile` server-to-server from Telegram's servers. Capacitor app is not in the data path for the original. |
| "GuardBox's app never decodes the original" | ✅ TRUE | Only ever decodes the CDR-reconstructed PNG returned from the backend. |
| "The original never reaches the gallery, file manager, or other apps" | ✅ TRUE | Confined to Telegram's private sandbox (if anywhere), never exposed beyond it. |

**Use in copy:** *"GuardBox receives the file directly from Telegram's servers — it
never travels through your device. You view a screenshot of the reconstructed clean
copy in the app — the file itself never travels to your phone."* Do not claim absolute
"never on the device's disk in any circumstance."

#### WhatsApp path — claim truth table (assumes required user posture configured)

| Claim | True / False | Notes |
|---|---|---|
| "Never saved to the gallery" | ✅ TRUE | With "Save to Camera Roll / Media visibility" off and the app never writing to the gallery. This is what users mean by "saved to my phone." |
| "Never in WhatsApp's sandbox" | ❌ FALSE | WhatsApp downloads the file to its private app sandbox in order to make it shareable. Outside GuardBox's control. |
| "Never on the device's disk at all" | ❌ FALSE | WhatsApp's sandbox is on disk, just walled off from other apps and the gallery. The strict version cannot be honored in the share-sheet model. |
| "Never decoded by any app other than WhatsApp's own download handler" | ✅ TRUE | GuardBox treats the bytes as opaque and streams them — never invokes an image parser on the original. The security-meaningful claim. |
| "GuardBox itself never saves the original to disk" | ✅ TRUE | True *only if* the Capacitor share handler streams bytes rather than caches them (see code-level rule below). |
| "Never exposed to other apps, gallery, or file managers" | ✅ TRUE | WhatsApp's sandbox is private to WhatsApp; GuardBox never copies it elsewhere. |

**Use in copy:** *"GuardBox doesn't save the original to your gallery, doesn't keep
it in GuardBox's own storage, and doesn't decode it on your phone. WhatsApp briefly
holds it in its own private storage in order to share it — that part is outside
GuardBox's control. With auto-download off, this only happens when you explicitly
choose to share. You view a screenshot of the reconstructed clean copy in the app —
the file itself is never sent to your phone."* Do not claim "never touches the device"
for the WhatsApp path.

### Required user posture — both messaging apps configured the same way

GuardBox's security claims assume the user has configured both Telegram and WhatsApp
with **auto-download OFF and auto-save OFF**. Onboarding must walk them through this;
the README and in-app first-run flow must show the exact settings. Without this
configuration, the strongest claims do not hold.

**Telegram (Settings → Data and Storage):**
- Automatic media download → OFF for mobile data, Wi-Fi, and roaming.
- Save to Gallery → OFF (Settings → Chat Settings → Save to Gallery).

**WhatsApp:**
- Settings → Storage and Data → Media auto-download → "No media" for mobile data,
  Wi-Fi, and roaming.
- Settings → Chats → Media visibility / Save to Camera Roll → OFF.

**Why this matters for the claims:**
- *With these settings off*, neither app fetches files to the device until the user
  explicitly taps to view or share. The user controls when the file leaves the
  platform's servers.
- *Without these settings off*, the messaging app's own parser may have already
  rendered a preview or saved a copy to the gallery before the user can route the
  file through GuardBox — meaning the original has touched the device *before*
  GuardBox ever sees it. That breaks the chain we're protecting.

**Capacitor share handler — code-level rule that backs this up:**
The share handler must **stream incoming file bytes directly from the OS share
intent to the backend upload endpoint**. Never use `Filesystem.readFile()` or any
approach that writes the file to GuardBox's app cache or temp storage before upload.
The bytes pass through device memory only, never to GuardBox-owned disk storage.

---

## Project structure

```
guardbox/
├── CLAUDE.md                          ← you are here
├── docs/
│   └── guardbox-portability-rules.md  ← full portability rules + decisions log
├── frontend/                          ← React app + Capacitor shell
│   ├── src/
│   ├── android/
│   ├── ios/
│   └── .env.template                  ← GUARDBOX_API_URL=
├── backend/
│   ├── api/                           ← HTTPS/REST endpoints (the only thing frontend calls)
│   │   ├── auth.py                    ← Login with Telegram
│   │   ├── files.py                   ← GET/POST/DELETE file endpoints
│   │   └── middleware.py              ← session token check
│   ├── intake/
│   │   ├── telegram_bot.py            ← Telegram bot adapter (server-to-server)
│   │   └── upload.py                  ← WhatsApp/share-sheet upload endpoint
│   ├── cdr/
│   │   └── sanitize.py                ← CDR core: decode → strip → rebuild (libvips)
│   ├── storage/
│   │   ├── interface.py               ← 5 operations: save/list/get/delete/move
│   │   ├── local.py                   ← KVM disk + JSON sidecars (self-hosted)
│   │   └── cloud.py                   ← S3 + Postgres (paid cloud)
│   ├── .env.template                  ← BOT_TOKEN=, STORAGE_BACKEND=, S3_ENDPOINT=, etc.
│   └── Dockerfile
└── docker-compose.yml                 ← runs frontend + backend + (MinIO if needed)
```

---

## Dual intake — two paths, one backend

```
TELEGRAM PATH                         WHATSAPP PATH
User → @GuardBoxBot                   User → Share sheet → Capacitor app
      | (server-to-server)                   | (POST /files/upload)
      +──────────────┬──────────────────────+
                     v
            CDR Sandbox (hardened Docker)
            decode → rebuild in memory (tmpfs)
                     v
            storage.save() ── interface ──+
                     v                     v
        STORAGE_BACKEND=local       STORAGE_BACKEND=cloud
        KVM disk + JSON sidecars    S3 + Postgres
                     v
            API → React viewer → Save / Delete
```

Both paths produce `{ file_bytes, user_id, source }` and feed the same `cdr/sanitize()`
and the same `storage.save()`. No path gets its own CDR or storage logic.

Tag every file with `source: telegram_bot | share_sheet` so the UI shows the correct
per-platform security claim.

---

## API contract (frontend ↔ backend)

| Endpoint | Who calls it | Purpose |
|---|---|---|
| `POST /auth` | Frontend | Login with Telegram, return session token |
| `POST /files/upload` | Capacitor app | Upload file for scanning (WhatsApp path) |
| `GET /files?state=pending` | Frontend | List user's pending images |
| `GET /files?state=saved` | Frontend | List user's saved images |
| `GET /files/{id}` | Frontend | CDR metadata (what was stripped) |
| `GET /files/{id}/image` | Frontend | Stream the clean PNG |
| `POST /files/{id}/save` | Frontend | Move pending → saved |
| `DELETE /files/{id}` | Frontend | Remove file |

Frontend reads `GUARDBOX_API_URL` from env and calls only these endpoints. It never
talks to storage, the bot, or the sandbox directly.

---

## Build order

1. **Storage interface** — the 5 operations as abstract contract + `local.py` implementation.
2. **CDR module** — libvips decode → strip metadata → re-encode PNG, in memory/tmpfs.
3. **Telegram bot adapter** — receive forwarded file, pull from TG servers, run CDR, store.
4. **API endpoints** — wire frontend to real storage (replace mock SEED data).
5. **Identity** — Login with Telegram (links bot intake to app viewer by Telegram user ID).
6. **WhatsApp share-sheet handler** — Capacitor intake, POST /files/upload.
7. **docker-compose** — one-command self-hosted install.
8. **Hardening** — seccomp/AppArmor profiles, --cap-drop ALL, --network none, --rm.

---

## Useful commands (fill in as scripts are created)

```
# (placeholder — add real commands as they exist)
# ./scripts/build.sh          — build all containers
# ./scripts/run-dev.sh        — docker-compose up for local dev
# ./scripts/run-cdr-tests.sh  — CDR correctness + re-validation tests
# ./scripts/run-security-tests.sh — sandbox hardening verification
```

---

## What NOT to do (common traps)

- Don't import `storage/local.py` or `storage/cloud.py` outside of `storage/`.
- Don't add SQLite to the self-hosted version. No database means no database.
- Don't scatter `if self_hosted:` / `if cloud:` through the codebase. The storage
  interface is the ONE place that fork lives.
- Don't use `@import url('https://fonts.googleapis.com/...')` or any external CDN.
- Don't claim E2E encryption, zero-click protection, or "never touches device" for
  the WhatsApp path. Don't claim "absolutely never on disk in any circumstance" for
  the Telegram path. Claims must match the intake mechanism — see the truth tables
  in the Security Claims section.
- Don't write CDR logic that modifies the input file. Always extract and rebuild fresh.
