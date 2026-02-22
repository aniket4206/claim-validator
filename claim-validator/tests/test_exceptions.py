"""Tests for exception hierarchy."""

from __future__ import annotations

from claim_validator import (
    ClaimValidatorError,
    CodeTableError,
    ConfigurationError,
    LLMError,
    ValidationError,
)


class TestExceptionHierarchy:
    def test_base_is_exception(self) -> None:
        assert issubclass(ClaimValidatorError, Exception)

    def test_validation_error_inherits_base(self) -> None:
        assert issubclass(ValidationError, ClaimValidatorError)

    def test_configuration_error_inherits_base(self) -> None:
        assert issubclass(ConfigurationError, ClaimValidatorError)

    def test_llm_error_inherits_base(self) -> None:
        assert issubclass(LLMError, ClaimValidatorError)

    def test_code_table_error_inherits_base(self) -> None:
        assert issubclass(CodeTableError, ClaimValidatorError)

    def test_catch_all_with_base(self) -> None:
        """All specific exceptions are catchable via ClaimValidatorError."""
        for exc_class in (ValidationError, ConfigurationError, LLMError, CodeTableError):
            try:
                raise exc_class("test message")
            except ClaimValidatorError as e:
                assert str(e) == "test message"
