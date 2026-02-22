"""Tests for MonetaryValidator — charge amount and total validation."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.monetary import MonetaryValidator


def _valid_claim_dict() -> dict:
    """Minimal claim dict with valid monetary values."""
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


# --- Valid monetary ---


class TestMonetaryValidatorValid:
    """Tests for valid monetary data producing zero findings."""

    def setup_method(self) -> None:
        self.validator = MonetaryValidator()

    def test_valid_charges_zero_findings(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        monetary_findings = [
            f for f in result.findings
            if f.code in (
                "INVALID_CHARGE_AMOUNT",
                "CHARGE_TOTAL_MISMATCH",
            )
        ]
        assert monetary_findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "MonetaryValidator"

    def test_multiple_lines_valid_charges(self) -> None:
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
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        charge_findings = [
            f for f in result.findings
            if f.code == "INVALID_CHARGE_AMOUNT"
        ]
        assert charge_findings == []

    def test_total_charge_matches_line_sum(self) -> None:
        data = _valid_claim_dict()
        data["total_charge"] = 150.00
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert mismatch_findings == []


# --- Invalid charge amounts ---


class TestMonetaryValidatorCharges:
    """Tests for invalid charge amount detection."""

    def setup_method(self) -> None:
        self.validator = MonetaryValidator()

    def test_zero_charge_amount(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = 0.0
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_CHARGE_AMOUNT"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "charge_amount"
        assert findings[0].line_number == 1

    def test_negative_charge_amount(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = -50.00
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_CHARGE_AMOUNT"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_multiple_invalid_charges(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 0.0,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": -10.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_CHARGE_AMOUNT"
        ]
        assert len(findings) == 2
        assert {f.line_number for f in findings} == {1, 2}

    def test_empty_lines_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_CHARGE_AMOUNT"
        ]
        assert findings == []

    def test_charge_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = 0.0
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_CHARGE_AMOUNT"
        ]
        assert findings[0].suggestion != ""


# --- Total charge mismatch ---


class TestMonetaryValidatorTotal:
    """Tests for total charge mismatch detection."""

    def setup_method(self) -> None:
        self.validator = MonetaryValidator()

    def test_total_charge_mismatch(self) -> None:
        data = _valid_claim_dict()
        data["total_charge"] = 999.99
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "total_charge"

    def test_total_charge_none_no_finding(self) -> None:
        data = _valid_claim_dict()
        # total_charge defaults to None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert mismatch_findings == []

    def test_total_charge_within_tolerance(self) -> None:
        data = _valid_claim_dict()
        # 150.00 + 0.005 rounding diff
        data["total_charge"] = 150.005
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert mismatch_findings == []

    def test_total_charge_outside_tolerance(self) -> None:
        data = _valid_claim_dict()
        data["total_charge"] = 150.02
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert len(mismatch_findings) == 1

    def test_total_with_units(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = 50.00
        data["lines"][0]["units"] = 3.0
        data["total_charge"] = 150.00
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert mismatch_findings == []

    def test_total_with_units_mismatch(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = 50.00
        data["lines"][0]["units"] = 3.0
        data["total_charge"] = 50.00  # Wrong — should be 150
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert len(mismatch_findings) == 1

    def test_total_multiple_lines(self) -> None:
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
            },
        ]
        data["total_charge"] = 350.00
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert mismatch_findings == []

    def test_total_mismatch_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["total_charge"] = 999.99
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert findings[0].suggestion != ""

    def test_empty_lines_with_total_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = []
        data["total_charge"] = 100.00
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mismatch_findings = [
            f for f in result.findings
            if f.code == "CHARGE_TOTAL_MISMATCH"
        ]
        assert mismatch_findings == []


# --- Finding quality ---


class TestMonetaryValidatorFindings:
    """Tests for finding quality — no PHI, correct fields."""

    def setup_method(self) -> None:
        self.validator = MonetaryValidator()

    def test_no_phi_in_charge_messages(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = -50.00
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "-50" not in finding.message
            assert "-50" not in finding.suggestion

    def test_no_phi_in_total_messages(self) -> None:
        data = _valid_claim_dict()
        data["total_charge"] = 999.99
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "999.99" not in finding.message
            assert "999.99" not in finding.suggestion

    def test_all_severities_error(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["charge_amount"] = -1.0
        data["total_charge"] = 999.99
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert finding.severity == Severity.ERROR


# --- Statelessness ---


class TestMonetaryValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = MonetaryValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        bad_data = _valid_claim_dict()
        bad_data["lines"][0]["charge_amount"] = -1.0
        bad = ClaimData(**bad_data)

        r1 = self.validator.validate(good)
        r2 = self.validator.validate(bad)
        r3 = self.validator.validate(good)

        assert r1.findings == []
        assert len(r2.findings) >= 1
        assert r3.findings == []

    def test_returns_validator_output(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.validator_name == "MonetaryValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        self.validator.validate(claim)
        assert claim.lines[0].charge_amount == 150.00
