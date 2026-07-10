#!/bin/sh
# Generate a ready-to-use .env for self-hosted GuardBox.
# Run from the repo root: ./scripts/setup-env.sh [--force]
#
# Fills in everything that can be safely defaulted or generated
# (SESSION_SECRET, STORAGE_ROOT, GUARDBOX_BASE_URL, SESSION_SECURE_COOKIE)
# and interactively prompts only for BOT_TOKEN, the one value that can't
# be automated (it only exists after you register a bot with @BotFather).

set -e

cd "$(dirname "$0")/.."

FORCE=0
if [ "$1" = "--force" ]; then
    FORCE=1
fi

if [ -f .env ] && [ "$FORCE" -ne 1 ]; then
    echo "ERROR: .env already exists. Refusing to overwrite." >&2
    echo "       Re-run with --force if you really want to regenerate it." >&2
    exit 1
fi

if ! command -v python3 > /dev/null 2>&1; then
    echo "ERROR: python3 is required to generate SESSION_SECRET" >&2
    exit 1
fi

cp backend/.env.template .env

# Escape sed replacement-string metacharacters: backslash, ampersand, and our delimiter.
escape_sed() {
    printf '%s' "$1" | sed -e 's/[\&|]/\\&/g'
}

set_env_var() {
    key="$1"
    value="$(escape_sed "$2")"
    sed -i "s|^${key}=.*|${key}=${value}|" .env
}

echo "==> Generating SESSION_SECRET..."
SESSION_SECRET="$(python3 -c "import secrets; print(secrets.token_hex(32))")"
set_env_var "SESSION_SECRET" "$SESSION_SECRET"

echo "==> Filling in self-hosted defaults..."
set_env_var "STORAGE_ROOT" "/data/guardbox"
set_env_var "GUARDBOX_BASE_URL" "http://localhost:8000"
set_env_var "SESSION_SECURE_COOKIE" "false"

echo ""
echo "Telegram bot token (optional — needed only for the Telegram intake path)."
echo "Get one from @BotFather on Telegram: send /newbot and follow the prompts."
printf "Paste your bot token, or press Enter to skip for now: "
read -r BOT_TOKEN

if [ -n "$BOT_TOKEN" ]; then
    set_env_var "BOT_TOKEN" "$BOT_TOKEN"
else
    echo "Skipped — Telegram intake will be disabled until you set BOT_TOKEN in .env and restart."
fi

echo ""
echo "==> .env is ready."
echo "    Auto-filled: SESSION_SECRET, STORAGE_ROOT, GUARDBOX_BASE_URL, SESSION_SECURE_COOKIE"
if [ -n "$BOT_TOKEN" ]; then
    echo "    BOT_TOKEN:   set"
else
    echo "    BOT_TOKEN:   not set (Telegram intake disabled)"
fi
echo ""
echo "Next: ./scripts/build.sh && docker compose up -d"
