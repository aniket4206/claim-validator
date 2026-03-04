"""Tests for clearinghouse exception hierarchy."""

from __future__ import annotations

import pytest

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
    ClearinghouseValidationError,
)
from claim_validator.exceptions import ClaimValidatorError


class TestClearinghouseErrorHierarchy:
    """Verify exception inheritance and instantiation."""

    def test_clearinghouse_error_inherits_from_base(self) -> None:
        assert issubclass(ClearinghouseError, ClaimValidatorError)

    def test_auth_error_inherits_from_clearinghouse(self) -> None:
        assert issubclass(ClearinghouseAuthError, ClearinghouseError)

    def test_validation_error_inherits_from_clearinghouse(self) -> None:
        assert issubclass(ClearinghouseValidationError, ClearinghouseError)

    def test_timeout_error_inherits_from_clearinghouse(self) -> None:
        assert issubclass(ClearinghouseTimeoutError, ClearinghouseError)

    def test_server_error_inherits_from_clearinghouse(self) -> None:
        assert issubclass(ClearinghouseServerError, ClearinghouseError)

    def test_all_catchable_as_clearinghouse_error(self) -> None:
        for exc_class in (
            ClearinghouseAuthError,
            ClearinghouseValidationError,
            ClearinghouseTimeoutError,
            ClearinghouseServerError,
        ):
            with pytest.raises(ClearinghouseError):
                raise exc_class("test")

    def test_all_catchable_as_claim_validator_error(self) -> None:
        for exc_class in (
            ClearinghouseError,
            ClearinghouseAuthError,
            ClearinghouseValidationError,
            ClearinghouseTimeoutError,
            ClearinghouseServerError,
        ):
            with pytest.raises(ClaimValidatorError):
                raise exc_class("test")

    def test_error_message_preserved(self) -> None:
        err = ClearinghouseAuthError("Invalid API key")
        assert str(err) == "Invalid API key"

    def test_error_with_no_message(self) -> None:
        err = ClearinghouseError()
        assert str(err) == ""


class TestClearinghouseImports:
    """Verify exceptions importable from top-level clearinghouse package."""

    def test_import_from_clearinghouse_package(self) -> None:
        from claim_validator.clearinghouse import (
            ClearinghouseAuthError,
            ClearinghouseError,
            ClearinghouseServerError,
            ClearinghouseTimeoutError,
            ClearinghouseValidationError,
        )

        assert ClearinghouseError is not None
        assert ClearinghouseAuthError is not None
        assert ClearinghouseValidationError is not None
        assert ClearinghouseTimeoutError is not None
        assert ClearinghouseServerError is not None
