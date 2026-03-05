"""Tests for ValidationContext — cross-stage passthrough tracker."""

from __future__ import annotations

import pytest

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.pipeline.context import (
    VALIDATOR_CATEGORY_MAP,
    ValidationContext,
    ValidatorResult,
)


class TestValidatorResult:
    """ValidatorResult dataclass tests."""

    def test_defaults(self):
        r = ValidatorResult(validator_name="NPIValidator", category="npi", passed=True)
        assert r.validator_name == "NPIValidator"
        assert r.category == "npi"
        assert r.passed is True
        assert r.findings == []

    def test_with_findings(self):
        f = Finding(
            code="INVALID_NPI",
            message="bad",
            severity=Severity.ERROR,
            field_name="npi",
        )
        r = ValidatorResult(
            validator_name="NPIValidator",
            category="npi",
            passed=False,
            findings=[f],
        )
        assert r.passed is False
        assert len(r.findings) == 1


class TestValidationContext:
    """ValidationContext record / query tests."""

    def test_empty_context_has_passed_false(self):
        ctx = ValidationContext()
        assert ctx.has_passed("npi") is False
        assert ctx.has_passed("member_id") is False

    def test_record_passed(self):
        ctx = ValidationContext()
        ctx.record("NPIValidator", "npi", passed=True)
        assert ctx.has_passed("npi") is True

    def test_record_failed_not_passed(self):
        ctx = ValidationContext()
        ctx.record("NPIValidator", "npi", passed=False)
        assert ctx.has_passed("npi") is False

    def test_get_prior_findings_empty(self):
        ctx = ValidationContext()
        assert ctx.get_prior_findings("npi") == []

    def test_get_prior_findings_returns_copy(self):
        f = Finding(
            code="INVALID_NPI",
            message="bad",
            severity=Severity.WARNING,
            field_name="npi",
        )
        ctx = ValidationContext()
        ctx.record("NPIValidator", "npi", passed=True, findings=[f])
        prior = ctx.get_prior_findings("npi")
        assert len(prior) == 1
        assert prior[0].code == "INVALID_NPI"
        # Verify it's a copy
        prior.clear()
        assert len(ctx.get_prior_findings("npi")) == 1

    def test_record_overwrites_previous(self):
        ctx = ValidationContext()
        ctx.record("NPIValidator", "npi", passed=True)
        assert ctx.has_passed("npi") is True
        ctx.record("PANPIValidator", "npi", passed=False)
        assert ctx.has_passed("npi") is False

    def test_multiple_categories(self):
        ctx = ValidationContext()
        ctx.record("NPIValidator", "npi", passed=True)
        ctx.record("MemberIDValidator", "member_id", passed=True)
        ctx.record("DemographicsValidator", "demographics", passed=False)
        assert ctx.has_passed("npi") is True
        assert ctx.has_passed("member_id") is True
        assert ctx.has_passed("demographics") is False


class TestValidatorCategoryMap:
    """Ensure the category map covers all expected validators."""

    @pytest.mark.parametrize(
        "validator_name,expected_category",
        [
            ("EligibilityNPIValidator", "npi"),
            ("PANPIValidator", "npi"),
            ("NPIValidator", "npi"),
            ("MemberIDValidator", "member_id"),
            ("PAMemberIDValidator", "member_id"),
            ("SubscriberIDValidator", "member_id"),
            ("EligibilityDemographicsValidator", "demographics"),
            ("DemographicsValidator", "demographics"),
        ],
    )
    def test_category_mapping(self, validator_name: str, expected_category: str):
        assert VALIDATOR_CATEGORY_MAP[validator_name] == expected_category

    def test_unknown_validator_not_in_map(self):
        assert "CodingValidator" not in VALIDATOR_CATEGORY_MAP
        assert "CompletenessValidator" not in VALIDATOR_CATEGORY_MAP
