#!/bin/sh
# Block destructive commands targeting GuardBox storage directories
COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command // ""')

case "$COMMAND" in
  *pending/*|*saved/*)
    case "$COMMAND" in
      rm\ -rf*|rm\ -r*|rmdir*|shred*)
        jq -n '{
          hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: "Destructive command targeting GuardBox storage (pending/ or saved/) is blocked. These directories contain user files. Delete individual files via the API instead."
          }
        }'
        exit 0
        ;;
    esac
    ;;
esac

exit 0
