#!/bin/sh
# Run pytest after every file edit inside backend/
FILE=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // .path // ""')

case "$FILE" in
  *backend/*)
    cd "${CLAUDE_PROJECT_DIR}/backend" && python -m pytest --tb=short -q
    ;;
  *)
    exit 0
    ;;
esac
