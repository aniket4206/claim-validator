"""Tests for CircuitBreaker."""

from __future__ import annotations

import time

import pytest

from claim_validator.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitBreakerStates:
    def test_initial_state_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_under_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_at_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_raises_on_check(self) -> None:
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        with pytest.raises(CircuitOpenError, match="open"):
            cb.check()

    def test_transitions_to_half_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_check(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        cb.check()  # Should not raise in HALF_OPEN

    def test_half_open_success_closes(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # Reset
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # Only 2 consecutive

    def test_failures_outside_window_reset(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, failure_window=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)  # Outside window
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # Counter reset


class TestCircuitBreakerPerInstance:
    def test_separate_instances_independent(self) -> None:
        cb1 = CircuitBreaker(failure_threshold=2)
        cb2 = CircuitBreaker(failure_threshold=2)
        cb1.record_failure()
        cb1.record_failure()
        assert cb1.state == CircuitState.OPEN
        assert cb2.state == CircuitState.CLOSED


class TestCircuitOpenError:
    def test_is_clearinghouse_error(self) -> None:
        from claim_validator.clearinghouse.exceptions import ClearinghouseError

        assert issubclass(CircuitOpenError, ClearinghouseError)
