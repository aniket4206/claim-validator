"""Tests for CompletenessValidator — required CMS-1500 field presence."""

from __future__ import annotations

import pytest

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.completeness import CompletenessValidator


def _complete_claim_dict() -> dict:
    """Minimal claim dict with all required fields populated."""
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


class TestCompletenessValidatorClaimLevel:
    """Tests for claim-level required field checks."""

    def setup_method(self) -> None:
        self.validator = CompletenessValidator()

    def test_complete_claim_has_zero_findings(self) -> None:
        claim = ClaimData(**_complete_claim_dict())
        result = self.validator.validate(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "CompletenessValidator"

    @pytest.mark.parametrize(
        "field",
        [
            "billing_provider_npi",
            "subscriber_id",
            "patient_first_name",
            "patient_last_name",
            "patient_dob",
            "patient_gender",
            "payer_id",
        ],
    )
    def test_missing_required_string_field(self, field: str) -> None:
        data = _complete_claim_dict()
        data[field] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == field]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR

    @pytest.mark.parametrize(
        "field",
        [
            "billing_provider_npi",
            "subscriber_id",
            "patient_first_name",
            "patient_last_name",
            "patient_dob",
            "patient_gender",
            "payer_id",
        ],
    )
    def test_empty_string_treated_as_missing(self, field: str) -> None:
        data = _complete_claim_dict()
        data[field] = ""
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == field]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR

    @pytest.mark.parametrize(
        "field",
        [
            "billing_provider_npi",
            "subscriber_id",
            "patient_first_name",
            "patient_last_name",
            "patient_dob",
            "patient_gender",
            "payer_id",
        ],
    )
    def test_whitespace_only_treated_as_missing(self, field: str) -> None:
        data = _complete_claim_dict()
        data[field] = "   "
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == field]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"

    def test_missing_diagnosis_codes_empty_list(self) -> None:
        data = _complete_claim_dict()
        data["diagnosis_codes"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "diagnosis_codes"]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR

    def test_missing_lines_empty_list(self) -> None:
        data = _complete_claim_dict()
        data["lines"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "lines"]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR

    def test_multiple_missing_fields_produce_multiple_findings(self) -> None:
        data = _complete_claim_dict()
        data["billing_provider_npi"] = None
        data["subscriber_id"] = ""
        data["patient_dob"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        missing_fields = {f.field_name for f in result.findings}
        assert "billing_provider_npi" in missing_fields
        assert "subscriber_id" in missing_fields
        assert "patient_dob" in missing_fields
        assert len(result.findings) >= 3


class TestCompletenessValidatorLineLevel:
    """Tests for line-level required field checks."""

    def setup_method(self) -> None:
        self.validator = CompletenessValidator()

    def test_line_missing_diagnosis_pointers(self) -> None:
        data = _complete_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "diagnosis_pointers"]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].line_number == 1

    def test_line_missing_service_date_from(self) -> None:
        data = _complete_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": None,
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "service_date_from"]
        assert len(findings) == 1
        assert findings[0].code == "MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].line_number == 1

    def test_line_empty_service_date_from(self) -> None:
        data = _complete_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "service_date_from"]
        assert len(findings) == 1
        assert findings[0].line_number == 1

    def test_line_number_is_one_indexed(self) -> None:
        data = _complete_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [],
                "charge_amount": 200.00,
                "service_date_from": "2026-01-15",
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "diagnosis_pointers"]
        assert len(findings) == 1
        assert findings[0].line_number == 2

    def test_multiple_lines_with_issues(self) -> None:
        data = _complete_claim_dict()
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [],
                "charge_amount": 150.00,
                "service_date_from": None,
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [],
                "charge_amount": 200.00,
                "service_date_from": None,
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        line_findings = [f for f in result.findings if f.line_number is not None]
        assert len(line_findings) == 4  # 2 fields x 2 lines
        line_numbers = {f.line_number for f in line_findings}
        assert line_numbers == {1, 2}


class TestCompletenessValidatorFindings:
    """Tests for finding quality — codes, suggestions, no PHI."""

    def setup_method(self) -> None:
        self.validator = CompletenessValidator()

    def test_all_finding_codes_are_missing_field(self) -> None:
        claim = ClaimData()  # Empty claim — everything missing
        result = self.validator.validate(claim)
        assert len(result.findings) > 0
        for finding in result.findings:
            assert finding.code == "MISSING_FIELD"

    def test_all_finding_severities_are_error(self) -> None:
        claim = ClaimData()
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert finding.severity == Severity.ERROR

    def test_all_findings_have_suggestions(self) -> None:
        claim = ClaimData()
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert finding.suggestion, f"Finding for {finding.field_name} has no suggestion"

    def test_messages_contain_no_phi(self) -> None:
        data = _complete_claim_dict()
        data["billing_provider_npi"] = None
        data["patient_first_name"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        phi_values = ["1234567893", "Jane", "Doe", "1990-01-15", "XYZ123456"]
        for finding in result.findings:
            for phi in phi_values:
                assert phi not in finding.message, f"PHI '{phi}' found in message"
                assert phi not in finding.suggestion, f"PHI '{phi}' found in suggestion"

    def test_field_name_matches_claim_attribute(self) -> None:
        data = _complete_claim_dict()
        data["payer_id"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.field_name == "payer_id"]
        assert len(findings) == 1


class TestCompletenessValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = CompletenessValidator()

    def test_multiple_calls_independent_results(self) -> None:
        good_claim = ClaimData(**_complete_claim_dict())
        bad_data = _complete_claim_dict()
        bad_data["billing_provider_npi"] = None
        bad_claim = ClaimData(**bad_data)

        result1 = self.validator.validate(good_claim)
        result2 = self.validator.validate(bad_claim)
        result3 = self.validator.validate(good_claim)

        assert result1.findings == []
        assert len(result2.findings) >= 1
        assert result3.findings == []

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(billing_provider_npi="1234567893")
        self.validator.validate(claim)
        assert claim.billing_provider_npi == "1234567893"

    def test_returns_validator_output(self) -> None:
        claim = ClaimData()
        result = self.validator.validate(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.validator_name == "CompletenessValidator"
