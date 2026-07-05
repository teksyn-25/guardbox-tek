#!/bin/sh
# Load .env at session start so all vars are available immediately
ENV_FILE="${CLAUDE_PROJECT_DIR}/backend/.env"

if [ -f "$ENV_FILE" ]; then
  while IFS= read -r line; do
    case "$line" in
      '#'*|'') continue ;;
    esac
    echo "export $line" >> "$CLAUDE_ENV_FILE"
  done < "$ENV_FILE"
fi
