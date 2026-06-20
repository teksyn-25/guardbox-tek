#!/bin/sh
# Run CDR-specific tests (sanitize + re-validation).
# Run from the repo root: ./scripts/run-cdr-tests.sh

set -e

cd "$(dirname "$0")/../backend"

echo "==> Running CDR tests..."
python -m pytest cdr/ --tb=short -v "$@"
