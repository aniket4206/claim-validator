"""Tests for CodingValidator — diagnosis/procedure code validation."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.coding import CodingValidator


def _valid_claim_dict() -> dict:
    """Minimal claim dict with valid coding."""
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


# --- Valid coding ---


class TestCodingValidatorValid:
    """Tests for valid coding producing zero findings."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_valid_coding_zero_findings(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "CodingValidator"

    def test_multiple_valid_diagnosis_codes(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "J06.9", "pointer": 1},
            {"code": "M54.5", "pointer": 2},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1, 2]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_valid_hcpcs_code(self) -> None:
        """HCPCS Level II codes are letter + 4 digits."""
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "J0120"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        proc_findings = [
            f for f in result.findings
            if f.code in (
                "INVALID_PROCEDURE_CODE",
                "INVALID_PROCEDURE_CODE_FORMAT",
            )
        ]
        # J0120 may or may not be in bundled table — only check format
        assert not any(
            f.code == "INVALID_PROCEDURE_CODE_FORMAT"
            for f in proc_findings
        )


# --- Diagnosis code validation ---


class TestCodingValidatorDiagnosis:
    """Tests for ICD-10-CM diagnosis code validation."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_invalid_diagnosis_code_not_in_table(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "Z99.99", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_CODE"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "diagnosis_codes"

    def test_invalid_diagnosis_code_format_too_short(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "J0", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_CODE_FORMAT"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_invalid_diagnosis_code_format_no_letter(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "12345", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_CODE_FORMAT"
        ]
        assert len(findings) == 1

    def test_invalid_diagnosis_code_format_special_chars(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "J06!9", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_CODE_FORMAT"
        ]
        assert len(findings) == 1

    def test_format_error_does_not_also_produce_table_error(self) -> None:
        """Format check short-circuits — no table lookup if format is wrong."""
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "XX", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dx_findings = [
            f for f in result.findings
            if f.code in (
                "INVALID_DIAGNOSIS_CODE_FORMAT",
                "INVALID_DIAGNOSIS_CODE",
            )
        ]
        assert len(dx_findings) == 1
        assert dx_findings[0].code == "INVALID_DIAGNOSIS_CODE_FORMAT"

    def test_empty_diagnosis_codes_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dx_findings = [
            f for f in result.findings
            if f.code in (
                "INVALID_DIAGNOSIS_CODE_FORMAT",
                "INVALID_DIAGNOSIS_CODE",
            )
        ]
        assert dx_findings == []

    def test_multiple_invalid_diagnosis_codes(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "Z99.99", "pointer": 1},
            {"code": "Q99.99", "pointer": 2},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1, 2]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_CODE"
        ]
        assert len(findings) == 2

    def test_diagnosis_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "Z99.99", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_CODE"
        ]
        assert findings[0].suggestion != ""


# --- Procedure code validation ---


class TestCodingValidatorProcedure:
    """Tests for CPT/HCPCS procedure code validation."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_invalid_procedure_code_not_in_table(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "00000"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_PROCEDURE_CODE"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "procedure_code"
        assert findings[0].line_number == 1

    def test_invalid_procedure_code_format_too_short(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "992"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_PROCEDURE_CODE_FORMAT"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].line_number == 1

    def test_invalid_procedure_code_format_too_long(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "992130"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_PROCEDURE_CODE_FORMAT"
        ]
        assert len(findings) == 1

    def test_invalid_procedure_code_format_special_chars(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "99-13"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_PROCEDURE_CODE_FORMAT"
        ]
        assert len(findings) == 1

    def test_format_error_does_not_also_produce_table_error(self) -> None:
        """Format check short-circuits — no table lookup if format wrong."""
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "99"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        proc_findings = [
            f for f in result.findings
            if f.code in (
                "INVALID_PROCEDURE_CODE_FORMAT",
                "INVALID_PROCEDURE_CODE",
            )
        ]
        assert len(proc_findings) == 1
        assert proc_findings[0].code == "INVALID_PROCEDURE_CODE_FORMAT"

    def test_empty_lines_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        proc_findings = [
            f for f in result.findings
            if f.code in (
                "INVALID_PROCEDURE_CODE_FORMAT",
                "INVALID_PROCEDURE_CODE",
            )
        ]
        assert proc_findings == []

    def test_multiple_lines_invalid_procedure_codes(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "00000",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "00001",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_PROCEDURE_CODE"
        ]
        assert len(findings) == 2
        assert {f.line_number for f in findings} == {1, 2}

    def test_procedure_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "00000"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_PROCEDURE_CODE"
        ]
        assert findings[0].suggestion != ""


# --- Modifier validation ---


class TestCodingValidatorModifier:
    """Tests for modifier format validation."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_valid_modifiers_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["modifiers"] = ["25", "59"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mod_findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert mod_findings == []

    def test_valid_alpha_modifier(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["modifiers"] = ["TC"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mod_findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert mod_findings == []

    def test_invalid_modifier_too_long(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["modifiers"] = ["259"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "modifiers"
        assert findings[0].line_number == 1

    def test_invalid_modifier_too_short(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["modifiers"] = ["2"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert len(findings) == 1

    def test_invalid_modifier_special_chars(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["modifiers"] = ["2!"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert len(findings) == 1

    def test_no_modifiers_no_findings(self) -> None:
        data = _valid_claim_dict()
        # Default claim has no modifiers
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        mod_findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert mod_findings == []

    def test_modifier_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["modifiers"] = ["259"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_MODIFIER_FORMAT"
        ]
        assert findings[0].suggestion != ""


# --- Diagnosis pointer validation ---


class TestCodingValidatorPointers:
    """Tests for diagnosis pointer consistency."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_valid_pointers_no_findings(self) -> None:
        data = _valid_claim_dict()
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        ptr_findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert ptr_findings == []

    def test_invalid_pointer_references_nonexistent(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "J06.9", "pointer": 1}]
        data["lines"][0]["diagnosis_pointers"] = [1, 5]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "diagnosis_pointers"
        assert findings[0].line_number == 1

    def test_multiple_invalid_pointers_on_one_line(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "J06.9", "pointer": 1}]
        data["lines"][0]["diagnosis_pointers"] = [5, 6]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert len(findings) == 2

    def test_invalid_pointers_across_lines(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "J06.9", "pointer": 1}]
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1, 5],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [7],
                "charge_amount": 200.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert len(findings) == 2
        assert {f.line_number for f in findings} == {1, 2}

    def test_empty_pointers_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["diagnosis_pointers"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        ptr_findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert ptr_findings == []

    def test_no_diagnosis_codes_no_pointer_findings(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        ptr_findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert ptr_findings == []

    def test_pointer_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["diagnosis_pointers"] = [1, 99]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DIAGNOSIS_POINTER"
        ]
        assert findings[0].suggestion != ""


# --- Unreferenced diagnosis ---


class TestCodingValidatorUnreferenced:
    """Tests for unreferenced diagnosis detection."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_all_referenced_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "J06.9", "pointer": 1},
            {"code": "M54.5", "pointer": 2},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1, 2]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        unref_findings = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert unref_findings == []

    def test_unreferenced_diagnosis_produces_warning(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "J06.9", "pointer": 1},
            {"code": "M54.5", "pointer": 2},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].field_name == "diagnosis_codes"

    def test_multiple_unreferenced_diagnoses(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "J06.9", "pointer": 1},
            {"code": "M54.5", "pointer": 2},
            {"code": "R10.9", "pointer": 3},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert len(findings) == 2

    def test_empty_diagnosis_codes_no_unreferenced_findings(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        unref_findings = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert unref_findings == []

    def test_empty_lines_no_unreferenced_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        unref_findings = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert unref_findings == []

    def test_unreferenced_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "J06.9", "pointer": 1},
            {"code": "M54.5", "pointer": 2},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert findings[0].suggestion != ""


# --- Finding quality ---


class TestCodingValidatorFindings:
    """Tests for finding quality — no PHI, correct fields."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_no_phi_in_diagnosis_messages(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "Z99.99", "pointer": 1}]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "Z99.99" not in finding.message
            assert "Z99.99" not in finding.suggestion

    def test_no_phi_in_procedure_messages(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["procedure_code"] = "00000"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "00000" not in finding.message
            assert "00000" not in finding.suggestion

    def test_error_severities_correct(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [{"code": "Z99.99", "pointer": 1}]
        data["lines"][0]["procedure_code"] = "00000"
        data["lines"][0]["diagnosis_pointers"] = [1]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            if finding.code != "UNREFERENCED_DIAGNOSIS":
                assert finding.severity == Severity.ERROR

    def test_warning_severity_for_unreferenced(self) -> None:
        data = _valid_claim_dict()
        data["diagnosis_codes"] = [
            {"code": "J06.9", "pointer": 1},
            {"code": "M54.5", "pointer": 2},
        ]
        data["lines"][0]["diagnosis_pointers"] = [1]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        unref = [
            f for f in result.findings
            if f.code == "UNREFERENCED_DIAGNOSIS"
        ]
        assert all(f.severity == Severity.WARNING for f in unref)


# --- Statelessness ---


class TestCodingValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = CodingValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        bad_data = _valid_claim_dict()
        bad_data["diagnosis_codes"] = [{"code": "Z99.99", "pointer": 1}]
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
        assert result.validator_name == "CodingValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        self.validator.validate(claim)
        assert claim.diagnosis_codes[0].code == "J06.9"
        assert claim.lines[0].procedure_code == "99213"
