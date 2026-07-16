"""
Ephemeral, process-local brute-force throttle for the single owner login.

Two project constraints shape this:
  - NO database (self-hosted rule) — so state lives in memory and resets on
    restart. There is nothing to install or back up.
  - Never store IP / client identity (metadata-minimization rule) — so there is
    no per-client key. There is only one owner account, so a single global
    counter is sufficient.

Mechanism: PROGRESSIVE DELAY, never a hard lockout. Each consecutive failed
attempt returns a longer delay for the caller to wait before responding
(0, 0.25, 0.5, 1, 2s, capped). A correct password resets the counter and is
never delayed — so a flood of wrong guesses slows an attacker without ever
locking the real owner out (which a global hard lockout would allow).

Callers apply the returned delay in their own idiom: sync endpoints time.sleep,
async endpoints await asyncio.sleep. This module never sleeps itself, which
keeps it trivially testable.
"""

_BASE_DELAY = 0.25
_MAX_DELAY = 2.0

_consecutive_failures = 0


def record_failure() -> float:
    """Register a failed login; return the seconds the caller should wait first."""
    global _consecutive_failures
    _consecutive_failures += 1
    if _consecutive_failures <= 1:
        return 0.0
    return min(_MAX_DELAY, _BASE_DELAY * 2 ** (_consecutive_failures - 2))


def record_success() -> None:
    """Register a successful login; clears any accumulated delay."""
    global _consecutive_failures
    _consecutive_failures = 0


def reset() -> None:
    """Clear all state. For tests and process re-init."""
    global _consecutive_failures
    _consecutive_failures = 0
