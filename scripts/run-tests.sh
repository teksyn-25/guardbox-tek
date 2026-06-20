#!/bin/sh
# Run the full GuardBox test suite.
# Run from the repo root: ./scripts/run-tests.sh
#
# Requires pyvips (libvips) to be installed on the host:
#   Ubuntu/Debian: apt-get install libvips-dev
#   Fedora:        dnf install vips-devel

set -e

cd "$(dirname "$0")/../backend"

if ! python -c "import pyvips" > /dev/null 2>&1; then
    echo "ERROR: pyvips not importable. Install libvips:" >&2
    echo "  Ubuntu/Debian: sudo apt-get install libvips-dev" >&2
    echo "  Fedora:        sudo dnf install vips-devel" >&2
    echo "  Then:          pip install pyvips" >&2
    exit 1
fi

echo "==> Running GuardBox test suite..."
python -m pytest --tb=short -q "$@"
