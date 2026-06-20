#!/bin/sh
# Run sandbox hardening verification tests.
# Run from the repo root: ./scripts/run-security-tests.sh
#
# Checks that docker-compose.yml, seccomp-profile.json, and Dockerfile
# enforce required security constraints (cap_drop, seccomp, read-only FS, etc.).

set -e

cd "$(dirname "$0")/../backend"

echo "==> Running security hardening tests..."
python -m pytest test_hardening.py --tb=short -v "$@"
