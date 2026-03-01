"""Tests for PANPIValidator."""

from __future__ import annotations

from datetime import date

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.npi import PANPIValidator


def _make_request(npi: str) -> PriorAuthRequest:
    return PriorAuthRequest(
        requester_npi=npi,
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
    )


class TestPANPIValidatorValid:
    """AC1: Valid NPI → zero findings."""

    def test_valid_npi_no_findings(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("1234567893"))
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("1234567893"))
        assert result.validator_name == "PANPIValidator"

    def test_another_valid_npi(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("1245319599"))
        assert len(result.findings) == 0


class TestPANPIValidatorInvalidFormat:
    """AC2: Invalid format → PA_INVALID_NPI_FORMAT."""

    def test_too_short(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("123"))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_NPI_FORMAT"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "requester_npi"

    def test_too_long(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("12345678901"))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_NPI_FORMAT"

    def test_non_numeric(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("123456789A"))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_NPI_FORMAT"

    def test_format_error_skips_luhn(self) -> None:
        """Format check fails → only format finding, no Luhn finding."""
        v = PANPIValidator()
        result = v.validate(_make_request("123"))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_NPI_FORMAT"


class TestPANPIValidatorLuhnFailure:
    """AC2: Valid format but Luhn fails → PA_INVALID_NPI."""

    def test_luhn_failure(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("1234567890"))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_NPI"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "requester_npi"

    def test_luhn_failure_message_no_phi(self) -> None:
        """AC11: Message references field name, not actual NPI value."""
        v = PANPIValidator()
        result = v.validate(_make_request("1234567890"))
        assert "1234567890" not in result.findings[0].message
        assert "requester_npi" in result.findings[0].message


class TestPANPIValidatorSkipEmpty:
    """Empty/whitespace NPI → skip validation (zero findings)."""

    def test_empty_string(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request(""))
        assert len(result.findings) == 0

    def test_whitespace_only(self) -> None:
        v = PANPIValidator()
        result = v.validate(_make_request("   "))
        assert len(result.findings) == 0
