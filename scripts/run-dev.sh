#!/bin/sh
# Start GuardBox in local dev mode.
# Run from the repo root: ./scripts/run-dev.sh
#
# Requires a .env file in the repo root (copy from backend/.env.template).
# SESSION_SECURE_COOKIE should be set to false for local HTTP dev.

set -e

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "ERROR: .env not found. Copy backend/.env.template to .env and fill in values." >&2
    exit 1
fi

if ! command -v docker > /dev/null 2>&1; then
    echo "ERROR: docker is not installed or not in PATH" >&2
    exit 1
fi

echo "==> Starting GuardBox (dev)..."
echo "    API:  http://127.0.0.1:8000"
echo "    Docs: http://127.0.0.1:8000/api/docs"
echo ""
docker compose up
