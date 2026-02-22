"""Tests for NPIValidator — Luhn check-digit validation."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.npi import NPIValidator, _check_luhn_npi


def _valid_claim_dict() -> dict:
    """Minimal claim dict with valid NPIs."""
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


# --- Luhn helper tests ---


class TestCheckLuhnNPI:
    """Direct tests for the _check_luhn_npi helper function."""

    def test_valid_npi_1234567893(self) -> None:
        assert _check_luhn_npi("1234567893") is True

    def test_invalid_npi_1234567890(self) -> None:
        assert _check_luhn_npi("1234567890") is False

    def test_invalid_npi_1234567891(self) -> None:
        assert _check_luhn_npi("1234567891") is False

    def test_valid_npi_1245319599(self) -> None:
        """Another known valid NPI."""
        assert _check_luhn_npi("1245319599") is True

    def test_valid_npi_1306849450(self) -> None:
        """Another known valid NPI."""
        assert _check_luhn_npi("1306849450") is True

    def test_non_numeric_returns_false(self) -> None:
        assert _check_luhn_npi("123456789A") is False

    def test_empty_string_returns_false(self) -> None:
        assert _check_luhn_npi("") is False


# --- Claim-level NPI validation ---


class TestNPIValidatorClaimLevel:
    """Tests for claim-level NPI field validation."""

    def setup_method(self) -> None:
        self.validator = NPIValidator()

    def test_valid_billing_npi_zero_findings(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "NPIValidator"

    def test_invalid_luhn_billing_npi(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "1234567890"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "billing_provider_npi"]
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI"
        assert findings[0].severity == Severity.ERROR

    def test_non_10_digit_billing_npi(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "123456789"  # 9 digits
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "billing_provider_npi"]
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI_FORMAT"
        assert findings[0].severity == Severity.ERROR

    def test_too_long_billing_npi(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "12345678901"  # 11 digits
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "billing_provider_npi"]
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI_FORMAT"

    def test_non_numeric_billing_npi(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "123456789A"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "billing_provider_npi"]
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI_FORMAT"

    def test_none_billing_npi_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        npi_findings = [
            f for f in result.findings
            if f.code in ("INVALID_NPI", "INVALID_NPI_FORMAT")
        ]
        assert npi_findings == []

    def test_empty_billing_npi_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = ""
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        npi_findings = [
            f for f in result.findings
            if f.code in ("INVALID_NPI", "INVALID_NPI_FORMAT")
        ]
        assert npi_findings == []

    def test_valid_rendering_npi(self) -> None:
        data = _valid_claim_dict()
        data["rendering_provider_npi"] = "1234567893"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_invalid_rendering_npi(self) -> None:
        data = _valid_claim_dict()
        data["rendering_provider_npi"] = "1234567890"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "rendering_provider_npi"]
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI"
        assert findings[0].line_number is None  # claim-level, not line-level

    def test_none_rendering_npi_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["rendering_provider_npi"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_both_npis_invalid_produces_two_findings(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "1234567890"
        data["rendering_provider_npi"] = "1234567891"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        field_names = {f.field_name for f in result.findings}
        assert "billing_provider_npi" in field_names
        assert "rendering_provider_npi" in field_names
        assert len(result.findings) == 2


# --- Line-level NPI validation ---


class TestNPIValidatorLineLevel:
    """Tests for line-level rendering NPI validation."""

    def setup_method(self) -> None:
        self.validator = NPIValidator()

    def test_line_valid_rendering_npi(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
                "rendering_provider_npi": "1234567893",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_line_invalid_rendering_npi(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
                "rendering_provider_npi": "1234567890",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.line_number is not None]
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI"
        assert findings[0].field_name == "rendering_provider_npi"
        assert findings[0].line_number == 1

    def test_line_none_rendering_npi_no_findings(self) -> None:
        data = _valid_claim_dict()
        # Default line has no rendering_provider_npi — should produce no findings
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_line_number_is_one_indexed(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": "2026-01-15",
                "rendering_provider_npi": "1234567890",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.line_number is not None]
        assert len(findings) == 1
        assert findings[0].line_number == 2

    def test_multiple_lines_with_invalid_npis(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
                "rendering_provider_npi": "1234567890",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": "2026-01-15",
                "rendering_provider_npi": "9999999999",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        line_findings = [f for f in result.findings if f.line_number is not None]
        assert len(line_findings) == 2
        assert {f.line_number for f in line_findings} == {1, 2}


# --- Finding quality ---


class TestNPIValidatorFindings:
    """Tests for finding quality — no PHI, correct suggestions."""

    def setup_method(self) -> None:
        self.validator = NPIValidator()

    def test_no_phi_in_messages(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "1234567890"
        data["rendering_provider_npi"] = "9876543210"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "1234567890" not in finding.message
            assert "9876543210" not in finding.message
            assert "1234567890" not in finding.suggestion
            assert "9876543210" not in finding.suggestion

    def test_suggestion_contains_registry_url(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "1234567890"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert len(result.findings) == 1
        assert "npiregistry.cms.hhs.gov" in result.findings[0].suggestion

    def test_all_severities_are_error(self) -> None:
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "123"  # format error
        data["rendering_provider_npi"] = "1234567890"  # luhn error
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert finding.severity == Severity.ERROR

    def test_format_error_does_not_also_produce_luhn_error(self) -> None:
        """Format check short-circuits — no Luhn check if format is wrong."""
        data = _valid_claim_dict()
        data["billing_provider_npi"] = "12345"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        billing_findings = [f for f in result.findings if f.field_name == "billing_provider_npi"]
        assert len(billing_findings) == 1
        assert billing_findings[0].code == "INVALID_NPI_FORMAT"


# --- Statelessness ---


class TestNPIValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = NPIValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        bad_data = _valid_claim_dict()
        bad_data["billing_provider_npi"] = "1234567890"
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
        assert result.validator_name == "NPIValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(billing_provider_npi="1234567893")
        self.validator.validate(claim)
        assert claim.billing_provider_npi == "1234567893"
