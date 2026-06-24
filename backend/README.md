# GuardBox Backend

FastAPI backend — CDR processing engine, REST API, and HTMX web UI.

## Quick Start

### 1. Install dependencies

```sh
# System (Ubuntu/Debian)
sudo apt-get install libvips-dev

# System (Fedora)
sudo dnf install vips-devel

# Python
pip install -r requirements.txt pytest
```

### 2. Run tests

```sh
python -m pytest --tb=short -q
```

All tests must pass before development.

### 3. Start the dev server

```sh
uvicorn app:app --reload
```

API at `http://localhost:8000` — interactive docs at `http://localhost:8000/api/docs`.

### 4. Configure environment

```sh
cp ../.env.template ../.env
```

Edit `.env`:

```sh
BOT_TOKEN=123456789:ABCdef...       # from @BotFather — enables Telegram file intake
GUARDBOX_BASE_URL=http://localhost:8000
SESSION_SECRET=<32 random hex bytes>
STORAGE_BACKEND=local
STORAGE_ROOT=/data/guardbox
SESSION_SECURE_COOKIE=false         # false for local HTTP dev only
```

---

## Architecture

### Request Flow

```
[User's browser]          [Flutter mobile app]     [Telegram servers]
      |                         |                         |
      | HTTP (web UI)           | HTTPS + Bearer          | server-to-server
      |                         |                         |
      +-------------------------+-------------------------+
                                |
                             app.py (FastAPI)
                                |
              +-----------------+-----------------+
              |                 |                 |
          api/auth          api/files         api/web
          api/middleware     (REST)            (HTMX)
              |                 |                 |
              +--------+--------+-----------------+
                       |
                 cdr/sanitize.py  (libvips)
                       |
               storage/interface.py
                       |
                 storage/local.py
                 (KVM disk + JSON sidecars)
```

### Directory Structure

```
backend/
├── app.py                  FastAPI entry point, router mounting, bot lifespan
├── admin_auth.py           Password auth — scrypt hash, setup flag, OWNER_ID
├── requirements.txt
├── Dockerfile
├── .env.template
│
├── api/
│   ├── auth.py             POST /api/auth — password login + first-run setup
│   ├── files.py            /api/files/* — list, get, save, delete (REST)
│   ├── web.py              /* — web UI routes (HTMX, HTML responses)
│   ├── middleware.py       Token verification — Bearer (REST) + HttpOnly cookie (web)
│   ├── test_auth.py
│   ├── test_files.py
│   └── test_web.py
│
├── intake/
│   ├── telegram_bot.py     Telegram bot poller (server-to-server, async)
│   └── upload.py           POST /api/files/upload — Flutter share-sheet intake
│
├── cdr/
│   └── sanitize.py         Decode → strip metadata → rebuild PNG (libvips)
│
├── storage/
│   ├── __init__.py         get_storage() dependency for FastAPI
│   ├── interface.py        Abstract contract — 5 operations
│   ├── local.py            KVM disk + JSON sidecars (self-hosted v1)
│   └── (cloud.py)          Not yet written — planned for v2 (S3 + Postgres)
│
├── templates/              Jinja2 HTML templates (HTMX + Alpine)
└── static/                 htmx.min.js, alpine.min.js (bundled, no CDN)
```

---

## Key Concepts

### Auth Flow

**First run:**
1. Visit `http://localhost:8000` → redirected to `/setup`
2. Create a password — stored as scrypt hash on disk (`admin_auth.py`)
3. Redirected to `/auth/login`

**Every login after:**
- Web UI: POST to `/auth/login` with password → HttpOnly session cookie set
- Flutter app: POST to `/api/auth` with password → Bearer token returned

User ID is always extracted from the token. It never comes from a query parameter.

### Storage Abstraction

All storage goes through `storage/interface.py` — 5 operations: `save`, `list`, `get`, `move`, `delete`.

Never import `storage/local.py` directly outside `storage/`. The backend is `STORAGE_BACKEND=local|cloud` at startup.

### Dual Intake

Both paths converge on the same CDR engine and storage interface:

**Telegram:** `intake/telegram_bot.py` → polls Telegram API → downloads file server-to-server → CDR → storage

**WhatsApp:** Flutter app → `POST /api/files/upload` (`intake/upload.py`) → CDR → storage

### Metadata Minimization

Only these fields are stored in the JSON sidecar:

```python
{
    "file_id": "uuid",
    "user_id": "owner",
    "source": "telegram_bot",     # telegram_bot | share_sheet
    "source_format": "jpeg",
    "stripped": ["exif", "xmp"],
    "output_format": "png",
    "dimensions": [1920, 1080],
}
```

No filename, no file size, no timestamp, no IP address. See `CLAUDE.md` for the full rule.

---

## Testing

Tests use real `LocalStorage` backed by `pytest tmp_path` — no storage mocks:

```python
@pytest.fixture
def storage(tmp_path):
    local = LocalStorage(root=str(tmp_path))
    app.dependency_overrides[get_storage] = lambda: local
    yield local
    app.dependency_overrides.clear()
```

Run a single test:

```sh
python -m pytest api/test_files.py::test_list_pending_returns_200 -v
```

---

## Debugging

```sh
# Verbose server logs
uvicorn app:app --log-level debug --reload

# Check environment
python -c "import os; print({k:v for k,v in os.environ.items() if 'GUARDBOX' in k or 'BOT' in k})"

# Inspect storage directly
python -c "
from storage.local import LocalStorage
s = LocalStorage(root='/data/guardbox')
print(s.list('owner', 'pending'))
"
```

## Common Issues

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: fastapi` | `pip install -r requirements.txt` |
| `libvips not found` | `sudo apt-get install libvips-dev` (or `dnf install vips-devel`) |
| `401 Unauthorized` on every request | Check `SESSION_SECRET` is set and consistent in `.env` |
| Tests hang | Check port 8000 is free: `lsof -i :8000` |

---

*Further reading: `CLAUDE.md` (design spec) · `docs/SECURITY.md` · `docs/dev-principles.md`*
