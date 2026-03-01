"""Tests for EligibilityDemographicsValidator."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.validators.rule_based.demographics import (
    EligibilityDemographicsValidator,
)


class TestDemographicsValidatorComplete:
    """Tests for complete subscriber info — zero findings."""

    def test_all_fields_present_no_findings(
        self, valid_request: EligibilityRequest
    ) -> None:
        validator = EligibilityDemographicsValidator()
        output = validator.validate(valid_request)
        assert len(output.findings) == 0

    def test_validator_name(self) -> None:
        assert (
            EligibilityDemographicsValidator.name
            == "EligibilityDemographicsValidator"
        )

    def test_with_relationship_self(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["relationship_code"] = "self"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_with_relationship_self_uppercase(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["relationship_code"] = "SELF"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0


class TestDemographicsValidatorMissingFields:
    """Tests for missing subscriber fields — ELIG_MISSING_FIELD."""

    def test_missing_first_name(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_first_name"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        findings = [f for f in output.findings if f.field_name == "subscriber_first_name"]
        assert len(findings) == 1
        assert findings[0].code == "ELIG_MISSING_FIELD"
        assert findings[0].severity == Severity.ERROR

    def test_missing_last_name(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_last_name"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        findings = [f for f in output.findings if f.field_name == "subscriber_last_name"]
        assert len(findings) == 1
        assert findings[0].code == "ELIG_MISSING_FIELD"

    def test_missing_subscriber_id(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        findings = [f for f in output.findings if f.field_name == "subscriber_id"]
        assert len(findings) == 1
        assert findings[0].code == "ELIG_MISSING_FIELD"

    def test_whitespace_only_treated_as_missing(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["subscriber_first_name"] = "   "
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        findings = [f for f in output.findings if f.field_name == "subscriber_first_name"]
        assert len(findings) == 1
        assert findings[0].code == "ELIG_MISSING_FIELD"

    def test_multiple_missing_produces_multiple_findings(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["subscriber_first_name"] = ""
        valid_request_dict["subscriber_last_name"] = ""
        valid_request_dict["subscriber_id"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        missing_field_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_FIELD"
        ]
        assert len(missing_field_findings) == 3

    def test_finding_has_suggestion(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_first_name"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        assert output.findings[0].suggestion != ""

    def test_no_phi_in_messages(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_first_name"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        for finding in output.findings:
            assert "Jane" not in finding.message
            assert "Doe" not in finding.message


class TestDemographicsValidatorDependentInfo:
    """Tests for dependent/patient info — ELIG_MISSING_DEPENDENT_INFO."""

    def test_no_relationship_code_no_dependent_check(
        self, valid_request: EligibilityRequest
    ) -> None:
        """When relationship_code is None, no dependent check is done."""
        validator = EligibilityDemographicsValidator()
        output = validator.validate(valid_request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert len(dependent_findings) == 0

    def test_relationship_self_no_dependent_check(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["relationship_code"] = "self"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert len(dependent_findings) == 0

    def test_spouse_with_all_patient_fields(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["relationship_code"] = "spouse"
        valid_request_dict["patient_first_name"] = "Alex"
        valid_request_dict["patient_last_name"] = "Doe"
        valid_request_dict["patient_dob"] = "2010-06-15"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert len(dependent_findings) == 0

    def test_child_missing_patient_fields(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["relationship_code"] = "child"
        # patient_first_name, patient_last_name, patient_dob all None
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert len(dependent_findings) == 1
        assert dependent_findings[0].severity == Severity.ERROR

    def test_dependent_finding_context_has_missing_fields(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        """Finding context includes which specific dependent fields are missing."""
        valid_request_dict["relationship_code"] = "child"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert dependent_findings[0].context is not None
        assert "missing_fields" in dependent_findings[0].context
        assert set(dependent_findings[0].context["missing_fields"]) == {
            "patient_first_name",
            "patient_last_name",
            "patient_dob",
        }

    def test_partial_dependent_context_lists_only_missing(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        """When only some patient fields are missing, context lists only those."""
        valid_request_dict["relationship_code"] = "spouse"
        valid_request_dict["patient_first_name"] = "Alex"
        # patient_last_name and patient_dob still None
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        missing = dependent_findings[0].context["missing_fields"]
        assert "patient_first_name" not in missing
        assert "patient_last_name" in missing
        assert "patient_dob" in missing

    def test_dependent_finding_field_name(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["relationship_code"] = "spouse"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert len(dependent_findings) == 1
        assert dependent_findings[0].field_name == "relationship_code"

    def test_dependent_finding_has_suggestion(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["relationship_code"] = "spouse"
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert "patient_first_name" in dependent_findings[0].suggestion

    def test_partial_patient_fields_still_triggers(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        """Even with some patient fields, missing any triggers the finding."""
        valid_request_dict["relationship_code"] = "spouse"
        valid_request_dict["patient_first_name"] = "Alex"
        # patient_last_name and patient_dob still None
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDemographicsValidator()
        output = validator.validate(request)
        dependent_findings = [
            f for f in output.findings if f.code == "ELIG_MISSING_DEPENDENT_INFO"
        ]
        assert len(dependent_findings) == 1
