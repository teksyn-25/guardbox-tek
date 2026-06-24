# GuardBox — Portability Rules (living document)

_Last updated: 2026-06-19 · update the Decisions Log and Revisit list as the project proceeds._

The goal: GuardBox runs identically whether self-hosted (Plan 1) or on a cloud
provider (Plan 2), and switching providers costs config changes, not a rewrite.

---

## The one principle

> **The code and the container image are identical everywhere. Only environment
> configuration and infrastructure differ.**

If changing where you deploy ever forces a change to application code, a portability
rule was broken. Fix the rule, not the symptom.

This is also your answer to reviewers/users who ask "what changes in the cloud
version?" -> *"Same code, same container, same runtime — only environment config and
infrastructure differ, by design, so anyone can self-host the identical build."*

---

## The one deliberate exception: storage (read this carefully)

There is exactly **one** place where Plan 1 and Plan 2 genuinely differ at the code
level, and it is intentional:

- **Self-hosted (Plan 1): NO database, ever.** Clean images are saved to disk in the
  KVM (`pending/{user_id}/` and `saved/{user_id}/`), and each file's metadata lives in
  a JSON sidecar next to it (`{file_id}.json`). Simplicity for a single person/org —
  nothing to install, back up, or recover.
- **Cloud / paid (Plan 2): ALWAYS a database.** Clean images go to S3-compatible object
  storage; metadata lives in Postgres. Needed for multi-user queries, billing, usage
  limits, search, analytics.

This divergence is allowed **only because it is sealed behind a single storage
interface.** Both designs implement the same five operations; the application code
above them is byte-for-byte identical. The difference lives entirely in the
`storage/` folder and leaks nowhere else.

### The storage interface (the contract both sides implement)

```
storage.save(user, file_bytes, metadata)      -> store clean file + its metadata
storage.list(user, state)                      -> list a user's pending|saved files
storage.get(user, file_id)                     -> fetch one clean file + metadata
storage.delete(user, file_id)                  -> remove file + metadata
storage.move(user, file_id, new_state)         -> pending -> saved
```

| Operation | Self-hosted (`local`) | Cloud (`cloud`) |
|---|---|---|
| save | write `.png` + `.json` sidecar to KVM disk | upload to S3 + insert Postgres row |
| list | read directory, parse sidecars | `SELECT ... WHERE user_id, state` |
| get | read `.png` + `.json` from disk | fetch S3 object + query Postgres |
| delete | remove `.png` + `.json` | delete S3 object + delete row |
| move | move files between folders | update row state + S3 key |

### Selected by one env var

```
STORAGE_BACKEND=local    # self-hosted: KVM disk + JSON sidecars, NO database
STORAGE_BACKEND=cloud    # paid: S3-compatible storage + Postgres database
```

At startup the backend loads the matching implementation. Nothing else in the codebase
changes.

### The hard rule for this exception

> All storage and metadata access goes through `storage/interface.py`. **No other file
> imports `local.py` or `cloud.py` directly.** The only place that picks an
> implementation is the startup factory, keyed off `STORAGE_BACKEND`. Adding a third
> backend = one new file implementing the interface, zero changes elsewhere.

Resist adding SQLite as a "middle ground" for self-hosted — a database is a database
(install, back up, corruption). The point of Plan 1 is no database at all. A
self-hoster who outgrows files-on-disk is ready for the cloud version.

---

## Do's

- [ ] Build standard OCI/Docker images. Same image runs on a laptop, bare metal, or any provider.
- [ ] All storage/metadata access goes through the storage interface — never call disk or S3 directly outside `storage/`.
- [ ] Use the S3-compatible API in the **cloud** backend (MinIO, Elastx "The Vault", Hetzner/Scaleway, AWS S3). Same SDK call everywhere it's used.
- [ ] Put every environment-specific value in env vars: `STORAGE_BACKEND`, storage path/endpoint, bucket, credentials, API hostname, region. Never hardcode.
- [ ] Treat the isolation runtime (runc / hardened Docker / gVisor / Kata) as a runtime-class/config choice, not an architecture choice. Same image, swappable runtime.
- [ ] Define infrastructure with **bash scripts in the self-hosted version**; switch to **Terraform for the cloud version** — kept in a separate folder from app code, edited instead of the source.
- [ ] Talk to backends over **HTTPS / TLS only — never plaintext HTTP.** Use standard web protocols (HTTPS/REST), not a provider's proprietary invocation mechanism.
- [ ] No runtime calls to third-party CDNs (fonts, scripts, analytics). Bundle everything; the app must run fully offline / air-gapped. (Self-host fonts, don't import Google Fonts.)
- [ ] Keep secrets out of the repo: commit `.env.template`, gitignore the real `.env`.
- [ ] Tag every file with its intake `source` (`telegram_bot` | `share_sheet`) so the UI can show the correct per-platform claim.
- [ ] Write the cloud deploy as the same steps a self-hoster follows — one set of docs serves both.

### Backend language strategy

- **v1:** Write the bot, API, orchestration, AND CDR core all in **Python**. The CDR
  logic is thin glue around C libraries (libvips via pyvips) that do the real parsing.
  Python gets us to a shippable demo in weeks.
- **v2:** Migrate the CDR hot path (the code that actually touches hostile bytes) to
  **Rust** — compiled as a standalone binary or a Python extension via PyO3. Rust's
  memory safety prevents the exact class of bugs (buffer overflows, use-after-free)
  that file-parser exploits target.
- The Python control plane (bot, API, orchestration) stays Python in v2. Only the CDR
  core migrates.

## Don'ts (these are what cause rewrites)

- [ ] No AWS Lambda-specific handlers or event formats in business logic.
- [ ] No proprietary managed services woven into code (DynamoDB, Cognito, provider queues). Hide any behind the interface.
- [ ] No hardcoded URLs, regions, bucket names, paths, or credentials.
- [ ] No provider-only SDKs in the core code path. Standard S3 SDK against any S3-compatible endpoint.
- [ ] No storage logic (disk or S3) anywhere except inside `storage/`.
- [ ] Don't let the build depend on a specific provider's CI/registry you can't reproduce locally.

---

## The code-vs-config line

| Bucket | Examples | Changes between Plan 1 and Plan 2? |
|---|---|---|
| **Code** | container images, app logic, runtime choice, API endpoints, the storage *interface* | No — identical |
| **Storage implementation** | `local.py` (KVM disk + JSON, no DB) vs `cloud.py` (S3 + Postgres) | Yes — the one deliberate divergence, sealed in `storage/` |
| **Config** | `STORAGE_BACKEND`, storage path/endpoint, bucket, region, DNS, TLS, credentials, API hostname | Yes — lives outside code |
| **New (additive)** | self-host: bash deploy scripts; cloud: Terraform, secrets wiring (provider TBD) | Written once, new files beside the app |

---

## Isolation tiers (runtime, not architecture)

Same OCI image across all four. Upgrade the tier without touching code.

1. **runc / plain Docker** — shared host kernel. Dev / first MVP.
2. **Hardened Docker** — seccomp + AppArmor, `--cap-drop ALL`, `--network none`, read-only fs, per-file ephemeral `--rm`, strict mem/CPU/pid limits.
3. **gVisor** — middle tier, runs on normal VMs, no special hardware.
4. **Kata + Firecracker / Cloud-Hypervisor** — strongest, needs KVM + bare metal.

Mental model: build the image once -> run under runc for dev -> run under Kata for the hardened path. The image and code do not change.

---

## Architecture at a glance

```
TELEGRAM PATH                         WHATSAPP PATH
User -> @GuardBoxBot                   User -> Share sheet -> Capacitor app
      | (bot, server-to-server)              | (POST /files/upload)
      +--------------+------------------------+
                     v
            CDR Sandbox (hardened Docker)
                     v
            storage.save()  -- interface --+
                     v                      v
        STORAGE_BACKEND=local        STORAGE_BACKEND=cloud
        KVM disk + JSON sidecars     S3 + Postgres
        (no database)                (database)
                     v
            API  ->  React viewer  ->  Save / Delete
```

---

## Decisions Log (append as decisions are made)

| Date | Decision | Rationale |
|---|---|---|
| 2026-06-19 | Plan 1 = self-hosted-first, Docker/OCI images | Open-source/grant positioning; portable |
| 2026-06-19 | Plan 2 = same containers on rented infra | One codebase, no lock-in |
| 2026-06-19 | **Self-hosted: NO database (KVM disk + JSON sidecars). Cloud: ALWAYS database (S3 + Postgres). Both behind one storage interface, chosen by STORAGE_BACKEND.** | Self-hosted stays dead-simple (no DB to run); cloud gets query power for billing/multi-user. App code identical; divergence sealed in storage/. |
| 2026-06-19 | Intake: Telegram bot (server-to-server) + WhatsApp share sheet (Capacitor) | Telegram = "never travels through your device" (with caveat: brief Telegram-sandbox cache during forward, depending on client); WhatsApp = "never decoded on your device, never saved to gallery, never stored in GuardBox's own storage" (WhatsApp's own private sandbox holds it briefly, outside our control). See CLAUDE.md truth tables for full precision. |
| 2026-06-19 | Frontend talks only to the backend API; bot is backend-side | Keeps the seam clean, frontend provider-agnostic |
| 2026-06-19 | **License: AGPL-3.0, dual-licensed with a commercial option for enterprise. Requires a CLA on all external contributions.** | Apache 2.0 let enterprises use the code free with no obligation to pay or contribute back — incompatible with "individuals free, enterprises pay." AGPL's network-copyleft clause makes enterprises buy the commercial license instead. CLA needed so GuardBox Labs can relicense contributed code commercially. |
| 2026-06-19 | **v1 backend: all Python (including CDR). v2: CDR core migrates to Rust via PyO3.** | Python ships fast for October; Rust adds memory safety to the hot path once funded. |
| _closed_ | Identity: Password login via GuardBox login page (set once on first run, no external auth) | Decision made — GuardBox owns the login page |
| _open_ | Cloud provider for Plan 2 | Candidates: Hetzner, Elastx (SE), Scaleway |
| _open_ | Isolation tier at launch | Start runc/hardened Docker -> Kata+Firecracker |
| _open_ | Keep AWS off the scope | Sovereignty claim depends on it |

## Revisit as the project grows

- [ ] Self-hosted: directory-listing performance once a user has thousands of files (the JSON-sidecar wall — that's the signal they're ready for cloud).
- [ ] Confirm chosen provider's exact S3-compatibility quirks before committing.
- [ ] Firecracker vs Cloud-Hypervisor under Kata on the chosen bare metal.
- [ ] Secrets management: .env now -> proper vault as the team grows.
- [ ] Async/job-queue if synchronous decode hits request time limits.
- [ ] Confirm bare-metal / nested-virt (KVM) availability on the chosen provider.
- [ ] Region selection (e.g. Stockholm) documented for the EU-hosted claim.
- [ ] Disk encryption (LUKS) on the self-hosted box so saved files aren't plaintext on a stolen disk.
