"""Tests for EligibilityResult model and passed property."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from claim_validator.constants import Severity
from claim_validator.eligibility.models.response import EligibilityResponse
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import Finding


def _make_finding(severity: Severity = Severity.ERROR) -> Finding:
    return Finding(
        code="ELIG_TEST",
        message="Test finding",
        severity=severity,
        field_name="test_field",
    )


class TestEligibilityResult:
    def test_defaults(self) -> None:
        result = EligibilityResult()
        assert result.eligible is None
        assert result.response is None
        assert result.findings == []
        assert result.ai_summary is None
        assert result.raw_response is None
        assert result.execution_time == 0.0

    def test_all_fields(self) -> None:
        response = EligibilityResponse(eligible=True)
        result = EligibilityResult(
            eligible=True,
            response=response,
            findings=[],
            ai_summary="Patient is eligible",
            raw_response={"raw": "data"},
            execution_time=0.05,
        )
        assert result.eligible is True
        assert result.response is not None
        assert result.ai_summary == "Patient is eligible"
        assert result.raw_response == {"raw": "data"}
        assert result.execution_time == 0.05

    def test_frozen(self) -> None:
        result = EligibilityResult()
        with pytest.raises(ValidationError):
            result.eligible = True  # type: ignore[misc]


class TestEligibilityResultPassed:
    """AC 4: passed property returns True only when zero ERROR findings."""

    def test_passed_true_no_findings(self) -> None:
        result = EligibilityResult()
        assert result.passed is True

    def test_passed_true_warning_only(self) -> None:
        result = EligibilityResult(findings=[_make_finding(Severity.WARNING)])
        assert result.passed is True

    def test_passed_false_with_error(self) -> None:
        result = EligibilityResult(findings=[_make_finding(Severity.ERROR)])
        assert result.passed is False

    def test_passed_false_mixed_findings(self) -> None:
        result = EligibilityResult(
            findings=[
                _make_finding(Severity.WARNING),
                _make_finding(Severity.ERROR),
            ]
        )
        assert result.passed is False

    def test_passed_true_multiple_warnings(self) -> None:
        result = EligibilityResult(
            findings=[
                _make_finding(Severity.WARNING),
                _make_finding(Severity.WARNING),
            ]
        )
        assert result.passed is True
