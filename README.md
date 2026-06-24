# GuardBox

**A sandboxed container for WhatsApp, Telegram, Signal, Messenger and email.**

Files and images are redirected and opened inside a single-use cloud sandbox, the moment they arrive — far from your device. The exploit isolates in the box.

GuardBox intercepts a file before any app on your device decodes it. It runs the file through a CDR (Content Disarm & Reconstruction) pipeline inside an isolated sandbox — stripping metadata, exploits, and hidden payloads — and returns a clean reconstructed copy. Your device never sees the original.

**Open-core · AGPL-3.0 · EU-hosted · Built in Stockholm**

---

## How it works

```
Incoming file (Telegram / WhatsApp)
        │
        ▼
  GuardBox sandbox
  ┌─────────────────────────────┐
  │  1. Identify from magic     │
  │     bytes (not extension)   │
  │  2. Decode in memory        │
  │  3. Strip all metadata      │
  │     (EXIF, XMP, GPS…)       │
  │  4. Re-encode as clean PNG  │
  └─────────────────────────────┘
        │
        ▼
  Clean image — safe to view
```

The original file is never written to disk, never decoded on your device, never passed to another app. You view a screenshot of the reconstructed copy — nothing else reaches you.

---

## Frontend architecture

GuardBox has two frontends — they coexist in every version and share the same backend API:

| Frontend | Where it lives | Available from |
|---|---|---|
| Web UI (HTMX + Jinja2) | `backend/templates/` + `backend/static/` | v1.0 — any browser |
| Mobile app (Flutter) | `mobile/` | v1.1 — WhatsApp share-sheet |

The web UI is server-rendered by Python (HTMX + Jinja2), tightly coupled to the backend routes, and lives inside `backend/` by design — no separate build step, no separate top-level directory. It is the primary interface for v1.0.

The Flutter app (`mobile/`) is the native mobile client. It calls only the `/api/*` REST endpoints and ships in v1.1 alongside the WhatsApp share-sheet intake. Both are frontends — neither replaces the other.

---

## Architecture

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  EXTERNAL WORLD                                                                  ║
║                                                                                  ║
║   [User's browser] ─────── HTTPS/HTTP ─────────────────────────────────────┐   ║
║   (web dashboard)                                                           │   ║
║                                                                             │   ║
║   [Telegram servers] ───────────────────────────────────────────────────┐  │   ║
║   (server-to-server,                                                    │  │   ║
║    never through device)                                                │  │   ║
║                                                                         │  │   ║
║   [Flutter mobile app] ── HTTPS + Bearer token ─────────────────────┐  │  │   ║
║   (v1.1 — /api/* only)                                               │  │  │   ║
║                                                                       │  │  │   ║
║   [WhatsApp share-sheet] ─ streams bytes ──────────────────────────┐ │  │  │   ║
║   (via Flutter, v1.1)                                               │ │  │  │   ║
╚═════════════════════════════════════════════════════════════════════╪═╪══╪══╪═══╝
                                                                      │ │  │  │
╔═════════════════════════════════════════════════════════════════════╪═╪══╪══╪════╗
║  HARDENED DOCKER CONTAINER  (cap_drop:ALL · seccomp · read-only fs) │ │  │  │    ║
║                                                                      │ │  │  │    ║
║  ┌───────────────────────────────────────────────────────────────────▼─▼──▼──▼──┐ ║
║  │                            app.py                                             │ ║
║  │                  FastAPI — router registry + bot lifespan                     │ ║
║  └────────────┬────────────────────┬───────────────────┬────────────────────────┘ ║
║               │                    │                   │                           ║
║        /api/auth            /api/files          /* + /upload                       ║
║               │                    │                   │                           ║
║  ┌────────────▼──────┐  ┌──────────▼────────┐  ┌──────▼─────────────────────┐    ║
║  │   api/auth.py     │  │   api/files.py    │  │      api/web.py             │    ║
║  │   password setup  │  │   list / get /    │  │  HTMX pages + partials      │    ║
║  │   + login →token  │  │   save / delete   │  │  setup · login · dashboard  │    ║
║  └────────────┬──────┘  └──────────┬────────┘  │  viewer · upload (HTML)     │    ║
║               │                    │            └──────┬──────────────────────┘    ║
║               └────────────────────┼──────────────────┘                           ║
║                                    │                                               ║
║  ┌─────────────────────────────────▼─────────────────────────────────────────┐    ║
║  │  api/middleware.py — token gate (Bearer REST / HttpOnly cookie web UI)    │    ║
║  └─────────────────────────────────┬─────────────────────────────────────────┘    ║
║                                    │                                               ║
║  ┌─────────────────────────────────▼─────────────────────────────────────────┐    ║
║  │  admin_auth.py — scrypt password hash on disk · OWNER_ID · setup flag    │    ║
║  └────────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                    ║
║  ── INTAKE ─────────────────────────────────────────────────────────────────────  ║
║                                                                                    ║
║  ┌──────────────────────────────┐      ┌──────────────────────────────────────┐   ║
║  │  intake/telegram_bot.py      │      │  intake/upload.py                    │   ║
║  │  polls Telegram API          │      │  POST /api/files/upload              │   ║
║  │  downloads image bytes       │      │  POST /upload (web UI)               │   ║
║  │  server-to-server            │      │  source = share_sheet                │   ║
║  │  source = telegram_bot       │      └──────────────┬───────────────────────┘   ║
║  └──────────────┬───────────────┘                     │                           ║
║                 └──────────────────┬──────────────────┘                           ║
║                                    │ raw bytes                                     ║
║  ── CDR SANDBOX ───────────────────▼──────────────  (tmpfs — nothing hits disk)   ║
║                                                                                    ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║  │  cdr/sanitize.py  (libvips / pyvips)                                        │  ║
║  │  magic bytes → decode in memory → strip metadata → re-encode clean PNG      │  ║
║  └─────────────────────────────────┬───────────────────────────────────────────┘  ║
║                                    │ clean bytes + CDR report                      ║
║  ── STORAGE ────────────────────── ▼───────────────────────────────────────────── ║
║                                                                                    ║
║  ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║  │  storage/interface.py — save · list · get · delete · move                   │  ║
║  └───────────────────────────────┬─────────────────────────────────────────────┘  ║
║                                  │ STORAGE_BACKEND env var                         ║
║              ┌───────────────────▼──────────────────┐                             ║
║              │  storage/local.py                     │                             ║
║              │  pending/{uid}/   saved/{uid}/        │                             ║
║              │  {file_id}.png  + {file_id}.json      │                             ║
║              └───────────────────────────────────────┘                             ║
║                          [guardbox_data Docker volume]                             ║
║                                                                                    ║
║  ── TEMPLATES / STATIC ─────────────────────────────────────────────────────────  ║
║  templates/  — Jinja2 (base, dashboard, login, setup, partials)                   ║
║  static/     — htmx.min.js · alpine.min.js  (bundled, no CDN calls)               ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

---

## v1 — Self-hosted

**Supported intake paths in v1:**
- **Telegram** — forward any image to your GuardBox bot. It is fetched server-to-server, sanitised, and appears in your dashboard. Your device never touches the original.
- **WhatsApp** — via the GuardBox mobile app (Flutter, coming in v1.1).

**What you get:**
- A hardened Docker container running the CDR pipeline
- A web dashboard accessible over HTTP on your local machine or network
- Login with a password you set on first run — no external account required
- Zero retention by default — delete anytime

> **Self-hosted runs over HTTP.** Since you control the machine, there is no third party in the path and no need for TLS between your browser and localhost. The Telegram bot connection is always server-to-server and is handled by Telegram's own TLS.

---

## Requirements

- A Linux machine (Fedora 39+, Ubuntu 22.04+, or Debian 12+)
- Docker CE + Docker Compose plugin
- A Telegram account to create a bot

---

## Installation

### 1. Install Docker

**Fedora:**
```sh
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

**Ubuntu / Debian:**
```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc > /dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Get the code

```sh
git clone https://github.com/teksyn-25/guardbox-tek.git guardbox
cd guardbox
```

### 3. Create your Telegram bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (looks like `123456789:ABCdef...`)
4. The **bot's numeric ID** is the number before the colon in the token

### 4. Configure

```sh
cp backend/.env.template .env
```

Edit `.env`:

```sh
BOT_TOKEN=123456789:ABCdef...          # from @BotFather
TELEGRAM_BOT_ID=123456789             # numeric part of the token (before the colon)
GUARDBOX_BASE_URL=http://localhost:8000
SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

STORAGE_BACKEND=local
STORAGE_ROOT=/data/guardbox

SESSION_SECURE_COOKIE=false            # HTTP is fine for self-hosted
```

### 5. Build and run

```sh
./scripts/build.sh
docker compose up -d
```

### 6. Open the dashboard

Go to **http://localhost:8000** in your browser. On first run you are redirected to **/setup** — create your password once. After that, log in at **/auth/login** with that password.

### 7. Forward an image

In Telegram, forward any image to your bot (`@YourBotName`).
It appears in your dashboard within seconds — clean, metadata-stripped, safe to view.

---

## Updating

```sh
git pull
docker compose build --no-cache
docker compose up -d
```

---

## Exposing over HTTPS (optional)

If you want GuardBox accessible from outside your local machine (remote server, VPS), put it behind a reverse proxy with TLS. **Caddy** handles certificate renewal automatically:

```sh
# Fedora
sudo dnf install caddy
# Ubuntu / Debian
sudo apt-get install caddy
```

`/etc/caddy/Caddyfile`:
```
yourdomain.com {
    reverse_proxy 127.0.0.1:8000
}
```

Then in `.env` update:
```sh
GUARDBOX_BASE_URL=https://yourdomain.com
SESSION_SECURE_COOKIE=true
```

```sh
sudo systemctl enable --now caddy
docker compose up -d
```

---

## Security

- **Sandboxed container:** `cap_drop: ALL`, `no-new-privileges`, read-only root filesystem, custom seccomp profile, tmpfs-only writes
- **Metadata stripped:** EXIF, XMP, GPS and all embedded metadata removed from every file
- **No retention by default:** files stay in `pending` until you explicitly save or delete them
- **HttpOnly cookie:** session token is never accessible to JavaScript
- **Non-root process:** container runs as a dedicated `guardbox` system user
- **Network binding:** Docker binds to `0.0.0.0:8000` — reachable on your local network. Put it behind a firewall or reverse proxy if exposed to the internet

### What GuardBox does not claim

- Does not claim end-to-end encryption (GuardBox must read the file to sanitise it)
- Does not claim zero-click protection (GuardBox enters the path only when you forward a file)
- Telegram path: the original *may* briefly cache in Telegram's private app sandbox during the forward action depending on client version — this is outside GuardBox's control

---

## Self-hosted vs. cloud

| | Self-hosted (v1) | Cloud (v2) |
|---|---|---|
| Transport | HTTP (localhost) | HTTPS |
| Storage | Files on disk + JSON sidecars | S3 + Postgres |
| Database | None | Postgres |
| CDR engine | Python + libvips | Rust (via PyO3) |
| Sandbox | Hardened Docker | Kata + Firecracker |
| License | AGPL-3.0 | Commercial license available |

---

## License

AGPL-3.0. See [LICENSE](LICENSE).
Commercial license available for enterprise deployments — contact guardboxlabs@protonmail.com.

A Contributor License Agreement (CLA) is required for external contributions.
