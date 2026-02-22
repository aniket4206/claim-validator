"""Tests for DuplicateValidator — duplicate claim line detection."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.duplicate import DuplicateValidator


def _valid_claim_dict() -> dict:
    """Minimal claim dict with no duplicate lines."""
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


# --- No duplicates ---


class TestDuplicateValidatorValid:
    """Tests for claims with no duplicate lines."""

    def setup_method(self) -> None:
        self.validator = DuplicateValidator()

    def test_no_duplicate_zero_findings(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "DuplicateValidator"

    def test_different_procedure_codes_no_duplicate(self) -> None:
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
        dup_findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert dup_findings == []

    def test_same_code_different_modifiers_no_duplicate(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "modifiers": ["25"],
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "modifiers": ["59"],
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dup_findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert dup_findings == []

    def test_same_code_different_dates_no_duplicate(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-16",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dup_findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert dup_findings == []


# --- Duplicate detection ---


class TestDuplicateValidatorDetection:
    """Tests for duplicate line detection."""

    def setup_method(self) -> None:
        self.validator = DuplicateValidator()

    def test_duplicate_lines_detected(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].field_name == "lines"
        assert findings[0].line_number == 2

    def test_duplicate_with_same_modifiers(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "modifiers": ["25", "59"],
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "modifiers": ["59", "25"],
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        # Sorted modifiers match — these are duplicates
        assert len(findings) == 1

    def test_triple_duplicate_two_findings(self) -> None:
        data = _valid_claim_dict()
        line = {
            "procedure_code": "99213",
            "diagnosis_pointers": [1],
            "charge_amount": 150.00,
            "service_date_from": "2026-01-15",
        }
        data["lines"] = [line.copy(), line.copy(), line.copy()]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert len(findings) == 2
        assert {f.line_number for f in findings} == {2, 3}

    def test_duplicate_different_charges_still_duplicate(self) -> None:
        """Charge amount is NOT part of the duplicate key."""
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert len(findings) == 1

    def test_empty_lines_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_duplicate_no_service_date(self) -> None:
        """Lines with no date: same code + modifiers = duplicate."""
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert len(findings) == 1


# --- Finding quality ---


class TestDuplicateValidatorFindings:
    """Tests for finding quality — no PHI, correct fields."""

    def setup_method(self) -> None:
        self.validator = DuplicateValidator()

    def test_no_phi_in_messages(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "99213" not in finding.message
            assert "99213" not in finding.suggestion

    def test_severity_is_warning(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert finding.severity == Severity.WARNING

    def test_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        assert findings[0].suggestion != ""

    def test_line_number_identifies_later_duplicate(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "DUPLICATE_LINE"
        ]
        # Line 2 is the duplicate, not line 1
        assert findings[0].line_number == 2


# --- Statelessness ---


class TestDuplicateValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = DuplicateValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        dup_data = _valid_claim_dict()
        dup_data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        bad = ClaimData(**dup_data)

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
        assert result.validator_name == "DuplicateValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        self.validator.validate(claim)
        assert claim.lines[0].procedure_code == "99213"
        assert claim.lines[0].charge_amount == 150.00
