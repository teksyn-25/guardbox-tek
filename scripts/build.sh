#!/bin/sh
# Build all GuardBox containers.
# Run from the repo root: ./scripts/build.sh

set -e

cd "$(dirname "$0")/.."

if ! command -v docker > /dev/null 2>&1; then
    echo "ERROR: docker is not installed or not in PATH" >&2
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo "ERROR: docker daemon is not running" >&2
    exit 1
fi

echo "==> Building GuardBox containers..."
docker compose build --no-cache

echo "==> Build complete."
