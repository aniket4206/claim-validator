"""Retry decorator for clearinghouse HTTP calls.

Uses ``tenacity`` when installed (via ``[resilience]`` extra).
Falls back to a no-op pass-through when tenacity is not available,
allowing clearinghouse calls to work without the resilience extra.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Retryable HTTP status codes
_RETRYABLE_STATUSES = {429, 502, 503, 504}

# Default retry configuration
_MAX_ATTEMPTS = 3
_INITIAL_WAIT = 1.0  # seconds
_MAX_WAIT = 30.0  # seconds
_BACKOFF_MULTIPLIER = 2.0


def _is_retryable(exc: BaseException) -> bool:
    """Determine if an exception warrants a retry."""
    if isinstance(exc, ClearinghouseTimeoutError):
        return True
    if isinstance(exc, ClearinghouseServerError):
        return True
    # ConnectionError, httpx.TimeoutException, etc.
    try:
        import httpx

        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
            return True
    except ImportError:
        pass
    return False


def retry_clearinghouse(func: F) -> F:
    """Decorator that retries clearinghouse calls on transient failures.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s, max 30s).
    Only retries on timeout, network errors, and 429/5xx responses.
    Does NOT retry on client errors (400, 401, 403, 404).

    Requires ``tenacity>=8.2`` (install via ``[resilience]`` extra).
    Without tenacity, the decorator is a no-op pass-through.
    """
    try:
        import tenacity
    except ImportError:
        # No tenacity installed — pass through without retry
        return func

    @tenacity.retry(
        retry=tenacity.retry_if_exception(_is_retryable),
        stop=tenacity.stop_after_attempt(_MAX_ATTEMPTS),
        wait=tenacity.wait_exponential(
            multiplier=_INITIAL_WAIT,
            max=_MAX_WAIT,
            exp_base=_BACKOFF_MULTIPLIER,
        ),
        before=lambda retry_state: logger.warning(
            "Retrying clearinghouse call (attempt %d/%d): %s",
            retry_state.attempt_number,
            _MAX_ATTEMPTS,
            retry_state.outcome.exception() if retry_state.outcome else "unknown",
        ),
        reraise=True,
    )
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
