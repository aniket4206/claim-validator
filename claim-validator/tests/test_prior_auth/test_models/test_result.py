"""Tests for prior authorization result models."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.models.response import PriorAuthResponse
from claim_validator.prior_auth.models.result import (
    PADeterminationResult,
    PriorAuthResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_finding(code: str = "PA_ERR") -> Finding:
    return Finding(code=code, message="error msg", severity=Severity.ERROR, field_name="field_a")


def _warning_finding(code: str = "PA_WARN") -> Finding:
    return Finding(
        code=code, message="warning msg", severity=Severity.WARNING, field_name="field_b"
    )


# ---------------------------------------------------------------------------
# PADeterminationResult
# ---------------------------------------------------------------------------


class TestPADeterminationResult:
    def test_create_required_true(self) -> None:
        result = PADeterminationResult(
            required=True,
            confidence="HIGH",
            reason="271 authOrCertIndicator=Y",
        )
        assert result.required is True
        assert result.confidence == "HIGH"
        assert result.reason == "271 authOrCertIndicator=Y"
        assert result.auth_or_cert_indicator is None
        assert result.free_text_indicators == []

    def test_create_required_false(self) -> None:
        result = PADeterminationResult(
            required=False,
            confidence="HIGH",
            reason="No PA indicator in 271 response",
        )
        assert result.required is False

    def test_create_with_all_fields(self) -> None:
        result = PADeterminationResult(
            required=True,
            confidence="MEDIUM",
            reason="Free-text indicator found",
            auth_or_cert_indicator="Y",
            free_text_indicators=["Prior authorization required"],
        )
        assert result.auth_or_cert_indicator == "Y"
        assert len(result.free_text_indicators) == 1

    def test_frozen(self) -> None:
        result = PADeterminationResult(
            required=True,
            confidence="HIGH",
            reason="test",
        )
        with pytest.raises(pydantic.ValidationError):
            result.required = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PriorAuthResult
# ---------------------------------------------------------------------------


class TestPriorAuthResult:
    def test_create_empty(self) -> None:
        result = PriorAuthResult()
        assert result.approved is None
        assert result.response is None
        assert result.findings == []
        assert result.ai_summary is None
        assert result.authorization_number is None
        assert result.raw_response is None
        assert result.execution_time == 0.0

    def test_create_approved(self) -> None:
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            authorization_number="AUTH789",
        )
        result = PriorAuthResult(
            approved=True,
            response=resp,
            authorization_number="AUTH789",
            execution_time=1.5,
        )
        assert result.approved is True
        assert result.response is not None
        assert result.response.is_approved is True
        assert result.authorization_number == "AUTH789"
        assert result.execution_time == 1.5

    def test_create_with_findings(self) -> None:
        result = PriorAuthResult(
            findings=[_error_finding(), _warning_finding()],
        )
        assert len(result.findings) == 2

    def test_frozen(self) -> None:
        result = PriorAuthResult()
        with pytest.raises(pydantic.ValidationError):
            result.approved = True  # type: ignore[misc]


class TestPriorAuthResultPassedProperty:
    def test_passed_with_no_findings(self) -> None:
        result = PriorAuthResult()
        assert result.passed is True

    def test_passed_with_warnings_only(self) -> None:
        result = PriorAuthResult(findings=[_warning_finding()])
        assert result.passed is True

    def test_failed_with_errors(self) -> None:
        result = PriorAuthResult(findings=[_error_finding()])
        assert result.passed is False

    def test_failed_with_mixed_findings(self) -> None:
        result = PriorAuthResult(
            findings=[_warning_finding(), _error_finding()],
        )
        assert result.passed is False

    def test_failed_with_multiple_errors(self) -> None:
        result = PriorAuthResult(
            findings=[_error_finding("E1"), _error_finding("E2")],
        )
        assert result.passed is False

    def test_model_validate_from_dict(self) -> None:
        """PriorAuthResult.model_validate(dict) works."""
        data = {
            "approved": True,
            "authorization_number": "AUTH789",
            "execution_time": 1.5,
            "findings": [],
        }
        result = PriorAuthResult.model_validate(data)
        assert result.approved is True
        assert result.authorization_number == "AUTH789"
        assert result.passed is True
