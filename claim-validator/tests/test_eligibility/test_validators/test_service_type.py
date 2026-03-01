"""Tests for ServiceTypeValidator."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.validators.rule_based.service_type import (
    ServiceTypeValidator,
)


class TestServiceTypeValidatorValid:
    """Tests for valid service type codes — zero findings."""

    def test_default_code_30_no_findings(
        self, valid_request: EligibilityRequest
    ) -> None:
        validator = ServiceTypeValidator()
        output = validator.validate(valid_request)
        assert len(output.findings) == 0

    def test_code_1_medical_care(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["service_type_code"] = "1"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_code_30_health_benefit_plan(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["service_type_code"] = "30"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_lowercase_code_accepted(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["service_type_code"] = "al"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_whitespace_trimmed(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["service_type_code"] = "  30  "
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_validator_name(self) -> None:
        assert ServiceTypeValidator.name == "ServiceTypeValidator"


class TestServiceTypeValidatorInvalid:
    """Tests for unknown service type codes — ELIG_INVALID_SERVICE_TYPE."""

    def test_unknown_code_produces_finding(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["service_type_code"] = "ZZZZ"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_SERVICE_TYPE"
        assert output.findings[0].severity == Severity.ERROR

    def test_finding_field_name(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["service_type_code"] = "ZZZZ"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "service_type_code"

    def test_finding_has_suggestion(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["service_type_code"] = "ZZZZ"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert output.findings[0].suggestion != ""

    def test_finding_has_context(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["service_type_code"] = "ZZZZ"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert output.findings[0].context is not None
        assert output.findings[0].context["submitted_code"] == "ZZZZ"

    def test_no_phi_in_message(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["service_type_code"] = "ZZZZ"
        request = EligibilityRequest(**valid_request_dict)
        validator = ServiceTypeValidator()
        output = validator.validate(request)
        assert "ZZZZ" not in output.findings[0].message
