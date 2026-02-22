"""Tests for SubscriberIDValidator — subscriber/insurance ID format validation."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.subscriber_id import SubscriberIDValidator


def _valid_claim_dict() -> dict:
    """Minimal claim dict with valid subscriber ID."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "patient_gender": "F",
        "payer_id": "BCBS001",
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ],
    }


# --- Valid subscriber IDs ---


class TestSubscriberIDValidatorValid:
    """Tests for valid subscriber IDs producing zero findings."""

    def setup_method(self) -> None:
        self.validator = SubscriberIDValidator()

    def test_valid_alphanumeric_subscriber_id(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        sub_findings = [
            f for f in result.findings if f.code == "INVALID_SUBSCRIBER_ID_FORMAT"
        ]
        assert sub_findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "SubscriberIDValidator"

    def test_numeric_only_subscriber_id(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "123456789"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_alpha_only_subscriber_id(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "ABCDEF"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_alphanumeric_with_dashes_subscriber_id(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "ABC-123-DEF"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_alphanumeric_with_special_chars(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "!!A@@"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []


# --- Skip None/empty ---


class TestSubscriberIDValidatorSkipEmpty:
    """Tests that None/empty subscriber IDs produce no findings."""

    def setup_method(self) -> None:
        self.validator = SubscriberIDValidator()

    def test_none_subscriber_id_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        sub_findings = [
            f for f in result.findings
            if f.code == "INVALID_SUBSCRIBER_ID_FORMAT"
        ]
        assert sub_findings == []

    def test_empty_subscriber_id_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = ""
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        sub_findings = [
            f for f in result.findings
            if f.code == "INVALID_SUBSCRIBER_ID_FORMAT"
        ]
        assert sub_findings == []

    def test_whitespace_subscriber_id_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "   "
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        sub_findings = [
            f for f in result.findings
            if f.code == "INVALID_SUBSCRIBER_ID_FORMAT"
        ]
        assert sub_findings == []


# --- Invalid subscriber IDs ---


class TestSubscriberIDValidatorInvalid:
    """Tests for invalid subscriber ID formats."""

    def setup_method(self) -> None:
        self.validator = SubscriberIDValidator()

    def test_only_special_characters(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "!!@@##$$"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings if f.code == "INVALID_SUBSCRIBER_ID_FORMAT"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "subscriber_id"

    def test_only_punctuation(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "---"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings if f.code == "INVALID_SUBSCRIBER_ID_FORMAT"
        ]
        assert len(findings) == 1

    def test_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "!!!"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert len(result.findings) == 1
        assert result.findings[0].suggestion != ""


# --- Finding quality ---


class TestSubscriberIDValidatorFindings:
    """Tests for finding quality — no PHI, correct fields."""

    def setup_method(self) -> None:
        self.validator = SubscriberIDValidator()

    def test_no_phi_in_messages(self) -> None:
        data = _valid_claim_dict()
        data["subscriber_id"] = "!!@@##"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "!!@@##" not in finding.message
            assert "!!@@##" not in finding.suggestion


# --- Statelessness ---


class TestSubscriberIDValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = SubscriberIDValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        bad_data = _valid_claim_dict()
        bad_data["subscriber_id"] = "!!!"
        bad = ClaimData(**bad_data)

        r1 = self.validator.validate(good)
        r2 = self.validator.validate(bad)
        r3 = self.validator.validate(good)

        assert r1.findings == []
        assert len(r2.findings) == 1
        assert r3.findings == []

    def test_returns_validator_output(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.validator_name == "SubscriberIDValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        self.validator.validate(claim)
        assert claim.subscriber_id == "XYZ123456"
