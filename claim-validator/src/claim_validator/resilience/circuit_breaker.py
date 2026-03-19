"""Per-instance circuit breaker for clearinghouse clients.

State machine: CLOSED → OPEN → HALF_OPEN → CLOSED (or back to OPEN).
Thread-safe via ``threading.Lock``.
"""

from __future__ import annotations

import threading
import time
from enum import StrEnum
from typing import Any, Callable, TypeVar

from claim_validator.clearinghouse.exceptions import ClearinghouseError

F = TypeVar("F", bound=Callable[..., Any])


class CircuitOpenError(ClearinghouseError):
    """Raised when the circuit breaker is open (provider unavailable)."""


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-instance circuit breaker for clearinghouse HTTP calls.

    Opens after ``failure_threshold`` consecutive failures within
    ``failure_window`` seconds.  After ``recovery_timeout`` seconds
    in OPEN state, transitions to HALF_OPEN and allows one request
    through.  Success closes the circuit; failure reopens it.

    Args:
        failure_threshold: Consecutive failures before opening.
        failure_window: Window (seconds) for counting failures.
        recovery_timeout: Seconds in OPEN before transitioning to HALF_OPEN.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        failure_window: float = 60.0,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._failure_window = failure_window
        self._recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        """Return current circuit state, auto-transitioning OPEN → HALF_OPEN."""
        with self._lock:
            if (
                self._state == CircuitState.OPEN
                and time.monotonic() - self._opened_at >= self._recovery_timeout
            ):
                self._state = CircuitState.HALF_OPEN
            return self._state

    def record_success(self) -> None:
        """Record a successful call — resets failure count, closes circuit."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call — may open the circuit."""
        with self._lock:
            now = time.monotonic()

            # Reset counter if outside failure window
            if now - self._last_failure_time > self._failure_window:
                self._failure_count = 0

            self._failure_count += 1
            self._last_failure_time = now

            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = now

            # In HALF_OPEN, any failure reopens immediately
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = now

    def check(self) -> None:
        """Check if the circuit allows a request.

        Raises:
            CircuitOpenError: If the circuit is OPEN.
        """
        current = self.state  # property handles OPEN → HALF_OPEN transition
        if current == CircuitState.OPEN:
            raise CircuitOpenError(
                "Circuit breaker is open — clearinghouse is unavailable"
            )
