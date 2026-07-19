"""
Tests for the ephemeral login throttle (progressive delay, no lockout).
"""

import pytest
import rate_limit


@pytest.fixture(autouse=True)
def _reset():
    rate_limit.reset()
    yield
    rate_limit.reset()


def test_first_failure_has_no_delay():
    assert rate_limit.record_failure() == 0.0


def test_delay_grows_then_caps():
    # 1st→0, then 0.25 doubling each consecutive failure, capped at 2.0s.
    delays = [rate_limit.record_failure() for _ in range(6)]
    assert delays == [0.0, 0.25, 0.5, 1.0, 2.0, 2.0]


def test_success_resets_the_counter():
    for _ in range(3):
        rate_limit.record_failure()
    rate_limit.record_success()
    # Owner who finally types the right password is not penalised on the next miss.
    assert rate_limit.record_failure() == 0.0


def test_reset_clears_state():
    for _ in range(4):
        rate_limit.record_failure()
    rate_limit.reset()
    assert rate_limit.record_failure() == 0.0
