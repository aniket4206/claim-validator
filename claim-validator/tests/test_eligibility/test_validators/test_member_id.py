"""Tests for MemberIDValidator."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.validators.rule_based.member_id import (
    MemberIDValidator,
)


class TestMemberIDValidatorValid:
    """Tests for well-formatted member IDs — zero findings."""

    def test_normal_id_no_findings(
        self, valid_request: EligibilityRequest
    ) -> None:
        validator = MemberIDValidator()
        output = validator.validate(valid_request)
        assert len(output.findings) == 0

    def test_min_two_alphanumeric(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "AB"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_mixed_with_dashes(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "A-1"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_long_id_valid(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "ABCDEFGHIJ123456789"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_numeric_only_id(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "12345"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_validator_name(self) -> None:
        assert MemberIDValidator.name == "MemberIDValidator"


class TestMemberIDValidatorInvalid:
    """Tests for malformed member IDs — ELIG_INVALID_MEMBER_ID."""

    def test_single_char_produces_finding(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["subscriber_id"] = "A"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_MEMBER_ID"
        assert output.findings[0].severity == Severity.ERROR

    def test_empty_string_produces_finding(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["subscriber_id"] = ""
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_MEMBER_ID"

    def test_non_alphanumeric_only_produces_finding(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["subscriber_id"] = "---"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_MEMBER_ID"

    def test_whitespace_only_produces_finding(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["subscriber_id"] = "   "
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_INVALID_MEMBER_ID"

    def test_finding_field_name(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "A"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "subscriber_id"

    def test_finding_has_suggestion(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "A"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert output.findings[0].suggestion != ""

    def test_finding_has_context(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "A-"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert output.findings[0].context is not None
        assert output.findings[0].context["alphanumeric_count"] == 1
        assert output.findings[0].context["id_length"] == 2

    def test_no_phi_in_message(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["subscriber_id"] = "A"
        request = EligibilityRequest(**valid_request_dict)
        validator = MemberIDValidator()
        output = validator.validate(request)
        assert "A" not in output.findings[0].message.split()
        # Also check actual subscriber ID isn't leaked
        assert "XYZ123456" not in output.findings[0].message
