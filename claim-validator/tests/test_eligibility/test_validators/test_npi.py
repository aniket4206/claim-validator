"""Tests for EligibilityNPIValidator."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.validators.rule_based.npi import (
    EligibilityNPIValidator,
)


class TestEligibilityNPIValidatorValid:
    """Tests for valid NPI — zero findings."""

    def test_valid_npi_no_findings(self, valid_request: EligibilityRequest) -> None:
        validator = EligibilityNPIValidator()
        output = validator.validate(valid_request)
        assert len(output.findings) == 0

    def test_validator_name(self) -> None:
        assert EligibilityNPIValidator.name == "EligibilityNPIValidator"

    def test_another_valid_npi(self) -> None:
        request = EligibilityRequest(
            provider_npi="1245319599",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="John",
            subscriber_last_name="Smith",
            subscriber_dob="1990-01-01",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_whitespace_npi_stripped(self) -> None:
        request = EligibilityRequest(
            provider_npi="  1234567893  ",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="John",
            subscriber_last_name="Smith",
            subscriber_dob="1990-01-01",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0


class TestEligibilityNPIValidatorInvalidFormat:
    """Tests for invalid NPI format — ELIG_INVALID_NPI_FORMAT."""

    def test_too_short(self) -> None:
        request = EligibilityRequest(
            provider_npi="12345",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_NPI_FORMAT"
        assert output.findings[0].severity == Severity.ERROR

    def test_too_long(self) -> None:
        request = EligibilityRequest(
            provider_npi="12345678901",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_NPI_FORMAT"

    def test_non_numeric(self) -> None:
        request = EligibilityRequest(
            provider_npi="12345ABCDE",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_NPI_FORMAT"

    def test_format_error_field_name(self) -> None:
        request = EligibilityRequest(
            provider_npi="123",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "provider_npi"


class TestEligibilityNPIValidatorLuhnFailure:
    """Tests for Luhn check-digit failure — ELIG_INVALID_NPI."""

    def test_luhn_failure(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567890",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_NPI"
        assert output.findings[0].severity == Severity.ERROR

    def test_luhn_failure_message_no_phi(self) -> None:
        """Finding message must not contain the actual NPI value."""
        request = EligibilityRequest(
            provider_npi="1234567890",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert "1234567890" not in output.findings[0].message

    def test_luhn_failure_field_name(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567890",
            payer_id="60054",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = EligibilityNPIValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "provider_npi"
