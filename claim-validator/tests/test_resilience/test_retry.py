"""Tests for retry_clearinghouse decorator."""

from __future__ import annotations

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
)
from claim_validator.resilience.retry import _is_retryable, retry_clearinghouse


class TestIsRetryable:
    def test_timeout_is_retryable(self) -> None:
        assert _is_retryable(ClearinghouseTimeoutError("timeout"))

    def test_server_error_is_retryable(self) -> None:
        assert _is_retryable(ClearinghouseServerError("500"))

    def test_value_error_not_retryable(self) -> None:
        assert not _is_retryable(ValueError("bad"))

    def test_runtime_error_not_retryable(self) -> None:
        assert not _is_retryable(RuntimeError("oops"))


class TestRetryDecorator:
    def test_decorator_does_not_break_function(self) -> None:
        """Decorated function should work normally on success."""

        @retry_clearinghouse
        def ok() -> str:
            return "success"

        assert ok() == "success"

    def test_decorator_passes_args(self) -> None:
        @retry_clearinghouse
        def add(a: int, b: int) -> int:
            return a + b

        assert add(2, 3) == 5
