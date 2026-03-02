"""Tests for the pre-claim orchestrator."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.response import EligibilityResponse
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import Finding
from claim_validator.models.workflow import PreClaimResult
from claim_validator.orchestrator import pre_claim_check
from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)


def _valid_eligibility_request() -> EligibilityRequest:
    return EligibilityRequest(
        provider_npi="1234567893",
        payer_id="60054",
        subscriber_id="XYZ123456",
        subscriber_first_name="Jane",
        subscriber_last_name="Doe",
        subscriber_dob="1985-03-15",
        date_of_service="2026-03-01",
        service_type_code="30",
    )


def _valid_pa_request() -> PriorAuthRequest:
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        diagnosis_codes=["J06.9"],
        service_lines=[
            ServiceLine(
                cpt_code="99213",
                from_date=date.today() + timedelta(days=10),
            ),
        ],
    )


def _elig_response_no_pa() -> EligibilityResponse:
    """Eligibility response where PA is not required (indicator=N)."""
    return EligibilityResponse(
        eligible=True,
        raw_response={
            "benefitsInformation": [
                {"authOrCertIndicator": "N"},
            ],
        },
    )


def _elig_response_pa_required() -> EligibilityResponse:
    """Eligibility response where PA is required (indicator=Y)."""
    return EligibilityResponse(
        eligible=True,
        raw_response={
            "benefitsInformation": [
                {"authOrCertIndicator": "Y"},
            ],
        },
    )


def _elig_response_pa_required_not_eligible() -> EligibilityResponse:
    """Eligibility response where PA is required but not eligible."""
    return EligibilityResponse(
        eligible=False,
        raw_response={
            "benefitsInformation": [
                {"authOrCertIndicator": "Y"},
            ],
        },
    )


class TestPreClaimResultModel:
    """Tests for the PreClaimResult model."""

    def test_default_values(self) -> None:
        result = PreClaimResult()
        assert result.ready_to_submit is False
        assert result.eligibility is None
        assert result.pa_determination is None
        assert result.pa_result is None
        assert result.findings == []
        assert result.ai_summary is None
        assert result.execution_time == 0.0

    def test_passed_no_findings(self) -> None:
        result = PreClaimResult()
        assert result.passed is True

    def test_passed_warnings_only(self) -> None:
        result = PreClaimResult(
            findings=[
                Finding(
                    code="TEST",
                    message="warn",
                    severity=Severity.WARNING,
                    field_name="x",
                ),
            ],
        )
        assert result.passed is True

    def test_not_passed_with_error(self) -> None:
        result = PreClaimResult(
            findings=[
                Finding(
                    code="TEST",
                    message="err",
                    severity=Severity.ERROR,
                    field_name="x",
                ),
            ],
        )
        assert result.passed is False

    def test_frozen(self) -> None:
        result = PreClaimResult()
        with pytest.raises(Exception):
            result.ready_to_submit = True  # type: ignore[misc]


class TestEligibilityOnly:
    """pre_claim_check with eligibility request only (no response, no PA)."""

    def test_valid_request_ready(self) -> None:
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
        )
        assert result.ready_to_submit is True
        assert result.passed is True
        assert result.eligibility is not None
        assert result.pa_determination is None
        assert result.pa_result is None
        assert result.execution_time > 0

    def test_invalid_npi_not_ready(self) -> None:
        req = EligibilityRequest(
            provider_npi="0000000000",  # Invalid NPI
            payer_id="60054",
            subscriber_id="XYZ123456",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        result = pre_claim_check(eligibility_request=req)
        assert result.ready_to_submit is False
        assert result.passed is False
        assert result.eligibility is not None
        assert result.pa_determination is None
        # Eligibility errors present
        error_codes = [f.code for f in result.findings if f.severity == Severity.ERROR]
        assert len(error_codes) > 0


class TestEligibleNoPaRequired:
    """Eligible + PA not required → ready_to_submit=True."""

    def test_eligible_no_pa(self) -> None:
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
            eligibility_response=_elig_response_no_pa(),
        )
        assert result.ready_to_submit is True
        assert result.pa_determination is not None
        assert result.pa_determination.required is False
        assert result.pa_result is None


class TestEligiblePaRequiredPasses:
    """Eligible + PA required + PA request passes → ready_to_submit=True."""

    def test_pa_passes(self) -> None:
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
            eligibility_response=_elig_response_pa_required(),
            pa_request=_valid_pa_request(),
        )
        assert result.ready_to_submit is True
        assert result.pa_determination is not None
        assert result.pa_determination.required is True
        assert result.pa_result is not None
        assert result.pa_result.passed is True


class TestEligiblePaRequiredFails:
    """Eligible + PA required + PA request fails → ready_to_submit=False."""

    def test_pa_fails(self) -> None:
        bad_pa = PriorAuthRequest(
            requester_npi="0000000000",  # Invalid NPI
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
            diagnosis_codes=["J06.9"],
            service_lines=[
                ServiceLine(
                    cpt_code="99213",
                    from_date=date.today() + timedelta(days=10),
                ),
            ],
        )
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
            eligibility_response=_elig_response_pa_required(),
            pa_request=bad_pa,
        )
        assert result.ready_to_submit is False
        assert result.pa_determination is not None
        assert result.pa_determination.required is True
        assert result.pa_result is not None
        assert result.pa_result.passed is False


class TestEligiblePaRequiredNoRequest:
    """Eligible + PA required + no pa_request → PA_REQUIRED warning."""

    def test_pa_required_no_request(self) -> None:
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
            eligibility_response=_elig_response_pa_required(),
        )
        assert result.ready_to_submit is False
        assert result.pa_determination is not None
        assert result.pa_determination.required is True
        assert result.pa_result is None

        pa_findings = [f for f in result.findings if f.code == "PA_REQUIRED"]
        assert len(pa_findings) == 1
        assert pa_findings[0].severity == Severity.WARNING


class TestEligibilityFails:
    """Eligibility fails → early return, no PA step."""

    def test_early_return_no_pa(self) -> None:
        req = EligibilityRequest(
            provider_npi="0000000000",  # Invalid NPI
            payer_id="60054",
            subscriber_id="XYZ123456",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        result = pre_claim_check(
            eligibility_request=req,
            eligibility_response=_elig_response_pa_required_not_eligible(),
            pa_request=_valid_pa_request(),
        )
        assert result.ready_to_submit is False
        # PA steps should not have run
        assert result.pa_determination is None
        assert result.pa_result is None


class TestSettingsPassthrough:
    """Settings and ai_config are passed through correctly."""

    def test_explicit_settings(self) -> None:
        settings = ClaimValidatorSettings()
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
            settings=settings,
        )
        assert result.ready_to_submit is True

    def test_ai_config_creates_settings(self) -> None:
        """ai_config without settings creates a new settings object."""
        with patch(
            "claim_validator.orchestrator.EligibilityPipeline.from_settings",
        ) as mock_from:
            mock_from.return_value = MagicMock(
                run=MagicMock(
                    return_value=EligibilityResult(findings=[]),
                ),
            )
            ai_config = {"provider": "openai", "api_key": "test", "model": "gpt-4"}
            pre_claim_check(
                eligibility_request=_valid_eligibility_request(),
                ai_config=ai_config,
            )
            call_settings = mock_from.call_args[0][0]
            assert call_settings.ai_config == ai_config

    def test_ai_config_overrides_settings(self) -> None:
        """ai_config overrides settings.ai_config."""
        original = ClaimValidatorSettings(
            ai_config={"provider": "anthropic", "api_key": "old", "model": "claude"},
        )
        with patch(
            "claim_validator.orchestrator.EligibilityPipeline.from_settings",
        ) as mock_from:
            mock_from.return_value = MagicMock(
                run=MagicMock(
                    return_value=EligibilityResult(findings=[]),
                ),
            )
            new_config = {"provider": "openai", "api_key": "new", "model": "gpt-4"}
            pre_claim_check(
                eligibility_request=_valid_eligibility_request(),
                settings=original,
                ai_config=new_config,
            )
            call_settings = mock_from.call_args[0][0]
            assert call_settings.ai_config == new_config


class TestAISummary:
    """AI summary propagation from eligibility result."""

    def test_ai_summary_propagated(self) -> None:
        with patch(
            "claim_validator.orchestrator.EligibilityPipeline.from_settings",
        ) as mock_from:
            mock_from.return_value = MagicMock(
                run=MagicMock(
                    return_value=EligibilityResult(
                        findings=[],
                        ai_summary="Patient is covered for vision services.",
                    ),
                ),
            )
            result = pre_claim_check(
                eligibility_request=_valid_eligibility_request(),
            )
            assert result.ai_summary == "Patient is covered for vision services."


class TestFindingsSorted:
    """Findings are sorted by severity (ERROR before WARNING)."""

    def test_errors_before_warnings(self) -> None:
        req = EligibilityRequest(
            provider_npi="0000000000",
            payer_id="INVALID",  # May produce warnings + errors
            subscriber_id="XYZ123456",
            subscriber_first_name="Jane",
            subscriber_last_name="Doe",
            subscriber_dob="1985-03-15",
        )
        result = pre_claim_check(eligibility_request=req)
        severities = [f.severity for f in result.findings]
        # All ERRORs should come before all WARNINGs
        error_indices = [i for i, s in enumerate(severities) if s == Severity.ERROR]
        warning_indices = [i for i, s in enumerate(severities) if s == Severity.WARNING]
        if error_indices and warning_indices:
            assert max(error_indices) < min(warning_indices)


class TestImports:
    """Verify the orchestrator and model are importable from the package."""

    def test_import_pre_claim_check(self) -> None:
        from claim_validator import pre_claim_check as fn

        assert callable(fn)

    def test_import_pre_claim_result(self) -> None:
        from claim_validator import PreClaimResult

        assert PreClaimResult is not None

    def test_import_from_orchestrator_module(self) -> None:
        from claim_validator.orchestrator import pre_claim_check as fn

        assert callable(fn)

    def test_import_from_workflow_module(self) -> None:
        from claim_validator.models.workflow import PreClaimResult as WorkflowResult

        assert WorkflowResult is not None


class TestExecutionTime:
    """Execution time is tracked."""

    def test_positive_execution_time(self) -> None:
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
        )
        assert result.execution_time > 0

    def test_execution_time_includes_pa(self) -> None:
        result = pre_claim_check(
            eligibility_request=_valid_eligibility_request(),
            eligibility_response=_elig_response_pa_required(),
            pa_request=_valid_pa_request(),
        )
        assert result.execution_time > 0
