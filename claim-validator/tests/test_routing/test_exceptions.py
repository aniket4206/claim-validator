"""Tests for PayerRoutingError exception."""

from __future__ import annotations

from claim_validator.exceptions import ClaimValidatorError, PayerRoutingError


class TestPayerRoutingError:
    """Tests for PayerRoutingError exception hierarchy."""

    def test_is_subclass_of_claim_validator_error(self) -> None:
        assert issubclass(PayerRoutingError, ClaimValidatorError)

    def test_is_subclass_of_exception(self) -> None:
        assert issubclass(PayerRoutingError, Exception)

    def test_raise_and_catch(self) -> None:
        with __import__("pytest").raises(PayerRoutingError, match="no routes"):
            raise PayerRoutingError("no routes available")

    def test_catch_as_base(self) -> None:
        try:
            raise PayerRoutingError("test")
        except ClaimValidatorError:
            pass  # Should be caught by base class
