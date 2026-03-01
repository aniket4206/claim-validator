"""Tests for PayerIDValidator."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.validators.rule_based.payer_id import PayerIDValidator


class TestPayerIDValidatorValid:
    """Tests for known payer IDs — zero findings."""

    def test_known_payer_aetna(self, valid_request: EligibilityRequest) -> None:
        validator = PayerIDValidator()
        output = validator.validate(valid_request)
        assert len(output.findings) == 0

    def test_known_payer_medicare(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="00882",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_known_payer_anthem_alpha_id(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="SB580",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_validator_name(self) -> None:
        assert PayerIDValidator.name == "PayerIDValidator"


class TestPayerIDValidatorInvalid:
    """Tests for unknown payer IDs — ELIG_INVALID_PAYER."""

    def test_unknown_payer_produces_finding(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="ZZZZZ",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_PAYER"
        assert output.findings[0].severity == Severity.ERROR

    def test_finding_field_name(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="ZZZZZ",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "payer_id"

    def test_finding_has_stedi_suggestion(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="ZZZZZ",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert "stedi" in output.findings[0].suggestion.lower()

    def test_finding_has_context_with_length(self) -> None:
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="ZZZZZ",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert output.findings[0].context is not None
        assert "payer_id_length" in output.findings[0].context

    def test_case_insensitive_lookup(self) -> None:
        """Lowercase alpha payer IDs should still be found."""
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="sb580",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_whitespace_payer_id(self) -> None:
        """Whitespace around payer ID should be handled."""
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="  60054  ",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_no_phi_in_message(self) -> None:
        """Finding message must not contain the actual payer ID."""
        request = EligibilityRequest(
            provider_npi="1234567893",
            payer_id="ZZZZZ",
            subscriber_id="ABC123",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        validator = PayerIDValidator()
        output = validator.validate(request)
        assert "ZZZZZ" not in output.findings[0].message
