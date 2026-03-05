"""Tests for clearinghouse pipeline integration (Story 5.5)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from claim_validator.clearinghouse import build_clearinghouse_client
from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.models.results import PipelineResult
from claim_validator.shared.pipeline.config import PipelineConfig
from claim_validator.shared.pipeline.engine import BasePipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockClearinghouseClient(BaseClearinghouseClient):
    """Minimal concrete implementation for testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(api_key="mock-key", base_url="https://mock.test", **kwargs)

    @property
    def provider_name(self) -> str:
        return "mock"

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        return ClearinghouseEligibilityResponse(
            status="active",
            eligible=True,
            raw_response={"status": "active"},
        )

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        return SubmissionResult(
            status="accepted",
            accepted=True,
            raw_response={"status": "accepted"},
        )

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        return ClaimStatusResponse(
            status="found",
            claim_status="paid",
            raw_response={"status": "found"},
        )


class _FailingClient(_MockClearinghouseClient):
    """Client that raises a configurable exception."""

    def __init__(self, exc: Exception, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._exc = exc

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        raise self._exc

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        raise self._exc

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        raise self._exc


# ---------------------------------------------------------------------------
# AC-1 / AC-2: Clearinghouse phase dispatch by domain
# ---------------------------------------------------------------------------


class TestClearinghousePhaseDispatch:
    """Verify _run_clearinghouse_phase dispatches correctly by domain."""

    def test_eligibility_domain_calls_check_eligibility(self) -> None:
        client = MagicMock(spec=BaseClearinghouseClient)
        client.check_eligibility.return_value = ClearinghouseEligibilityResponse(
            status="active", eligible=True, raw_response={},
        )
        config = PipelineConfig(
            domain="eligibility",
            clearinghouse_client=client,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        pipeline.run({"payer_id": "00520"})

        client.check_eligibility.assert_called_once_with({"payer_id": "00520"})
        client.submit_claim.assert_not_called()

    def test_claim_domain_calls_submit_claim(self) -> None:
        client = MagicMock(spec=BaseClearinghouseClient)
        client.submit_claim.return_value = SubmissionResult(
            status="accepted", accepted=True, raw_response={},
        )
        config = PipelineConfig(
            domain="claim",
            clearinghouse_client=client,
            code_prefix="CLM_",
        )
        pipeline = BasePipeline(config)
        pipeline.run({"payer_id": "00520"})

        client.submit_claim.assert_called_once_with({"payer_id": "00520"})
        client.check_eligibility.assert_not_called()

    def test_other_domain_calls_check_claim_status(self) -> None:
        client = MagicMock(spec=BaseClearinghouseClient)
        client.check_claim_status.return_value = ClaimStatusResponse(
            status="found", raw_response={},
        )
        config = PipelineConfig(
            domain="status",
            clearinghouse_client=client,
            code_prefix="STS_",
        )
        pipeline = BasePipeline(config)
        pipeline.run("REF-123")

        client.check_claim_status.assert_called_once_with("REF-123")


# ---------------------------------------------------------------------------
# AC-3: Graceful skip when not configured
# ---------------------------------------------------------------------------


class TestClearinghouseSkip:
    """Verify pipeline runs without clearinghouse when not configured."""

    def test_no_clearinghouse_client_skips_phase(self) -> None:
        config = PipelineConfig(
            domain="eligibility",
            clearinghouse_client=None,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        result = pipeline.run({"data": "test"})

        assert isinstance(result, PipelineResult)
        phase_names = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" not in phase_names
        assert "rule_based" in phase_names

    def test_clearinghouse_configured_adds_phase(self) -> None:
        client = _MockClearinghouseClient()
        config = PipelineConfig(
            domain="eligibility",
            clearinghouse_client=client,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        result = pipeline.run({"data": "test"})

        phase_names = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" in phase_names


# ---------------------------------------------------------------------------
# AC-4: Gating preserved
# ---------------------------------------------------------------------------


class TestClearinghouseGating:
    """Verify clearinghouse phase gating on rule failures."""

    def test_skip_clearinghouse_on_rule_failure(self) -> None:
        """When rules produce errors and gating is on, clearinghouse is skipped."""
        from claim_validator.models.results import Finding, ValidatorOutput
        from claim_validator.validators.base import BaseValidator

        class _FailingValidator(BaseValidator):
            name = "failing"

            def validate(self, data: Any) -> ValidatorOutput:
                return ValidatorOutput(
                    validator_name="failing",
                    findings=[
                        Finding(
                            code="TEST_FAIL",
                            message="Forced failure",
                            severity=Severity.ERROR,
                            field_name="test",
                        )
                    ],
                )

        client = MagicMock(spec=BaseClearinghouseClient)
        config = PipelineConfig(
            domain="eligibility",
            validators=(_FailingValidator(),),
            clearinghouse_client=client,
            skip_clearinghouse_on_rule_failure=True,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        result = pipeline.run({"data": "test"})

        phase_names = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" not in phase_names
        client.check_eligibility.assert_not_called()

    def test_clearinghouse_runs_when_gating_disabled(self) -> None:
        """When gating is disabled, clearinghouse runs even with rule errors."""
        from claim_validator.models.results import Finding, ValidatorOutput
        from claim_validator.validators.base import BaseValidator

        class _FailingValidator(BaseValidator):
            name = "failing"

            def validate(self, data: Any) -> ValidatorOutput:
                return ValidatorOutput(
                    validator_name="failing",
                    findings=[
                        Finding(
                            code="TEST_FAIL",
                            message="Forced failure",
                            severity=Severity.ERROR,
                            field_name="test",
                        )
                    ],
                )

        client = _MockClearinghouseClient()
        config = PipelineConfig(
            domain="eligibility",
            validators=(_FailingValidator(),),
            clearinghouse_client=client,
            skip_clearinghouse_on_rule_failure=False,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        result = pipeline.run({"data": "test"})

        phase_names = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" in phase_names


# ---------------------------------------------------------------------------
# AC-5: Settings-driven construction
# ---------------------------------------------------------------------------


class TestSettingsConstruction:
    """Verify build_clearinghouse_client builds from config dict."""

    def test_none_config_returns_none(self) -> None:
        assert build_clearinghouse_client(None) is None

    def test_empty_config_returns_none(self) -> None:
        assert build_clearinghouse_client({}) is None

    def test_builds_stedi_client(self) -> None:
        from claim_validator.clearinghouse.providers.stedi import StediClient

        client = build_clearinghouse_client(
            {"provider": "stedi", "api_key": "test-key"}
        )
        assert isinstance(client, StediClient)
        assert client.provider_name == "stedi"
        client.close()

    def test_does_not_mutate_input_dict(self) -> None:
        config = {"provider": "stedi", "api_key": "test-key"}
        original = dict(config)
        client = build_clearinghouse_client(config)
        assert config == original  # not mutated
        if client:
            client.close()

    def test_settings_clearinghouse_config_field(self) -> None:
        """ClaimValidatorSettings accepts clearinghouse_config."""
        settings = ClaimValidatorSettings(
            clearinghouse_config={"provider": "stedi", "api_key": "sk_test"}
        )
        assert settings.clearinghouse_config is not None
        assert settings.clearinghouse_config["provider"] == "stedi"


# ---------------------------------------------------------------------------
# AC-6: ClearinghouseError → findings
# ---------------------------------------------------------------------------


class TestClearinghouseErrorToFindings:
    """Verify clearinghouse exceptions map to appropriate findings."""

    def _run_with_error(
        self, exc: Exception, domain: str = "eligibility"
    ) -> PipelineResult:
        client = _FailingClient(exc)
        config = PipelineConfig(
            domain=domain,
            clearinghouse_client=client,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        return pipeline.run({"data": "test"})

    def test_validation_error_produces_warning(self) -> None:
        result = self._run_with_error(
            ClearinghouseValidationError("Missing PayerID")
        )
        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        findings = ch_phase.findings
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "CLEARINGHOUSE_VALIDATION" in findings[0].code
        assert "Missing PayerID" in findings[0].message

    def test_auth_error_produces_error(self) -> None:
        result = self._run_with_error(
            ClearinghouseAuthError("Invalid credentials")
        )
        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        findings = ch_phase.findings
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "CLEARINGHOUSE_AUTH" in findings[0].code

    def test_timeout_error_produces_error(self) -> None:
        result = self._run_with_error(
            ClearinghouseTimeoutError("Request timed out")
        )
        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        findings = ch_phase.findings
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "CLEARINGHOUSE_TIMEOUT" in findings[0].code

    def test_server_error_produces_error(self) -> None:
        result = self._run_with_error(
            ClearinghouseServerError("HTTP 500")
        )
        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        findings = ch_phase.findings
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "CLEARINGHOUSE_ERROR" in findings[0].code

    def test_generic_clearinghouse_error_produces_error(self) -> None:
        result = self._run_with_error(
            ClearinghouseError("Something went wrong")
        )
        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        findings = ch_phase.findings
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_unexpected_error_produces_error(self) -> None:
        result = self._run_with_error(RuntimeError("Unexpected"))
        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        findings = ch_phase.findings
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "CLEARINGHOUSE_ERROR" in findings[0].code

    def test_no_findings_on_success(self) -> None:
        client = _MockClearinghouseClient()
        config = PipelineConfig(
            domain="eligibility",
            clearinghouse_client=client,
            code_prefix="ELIG_",
        )
        pipeline = BasePipeline(config)
        result = pipeline.run({"data": "test"})

        ch_phase = [p for p in result.phase_results if p.phase == "clearinghouse"][0]
        assert len(ch_phase.findings) == 0


# ---------------------------------------------------------------------------
# AC-7: Orchestrator integration
# ---------------------------------------------------------------------------


class TestOrchestratorIntegration:
    """Verify clearinghouse_config wiring in orchestrator and API."""

    def test_orchestrator_accepts_clearinghouse_config(self) -> None:
        """pre_claim_check passes clearinghouse_config to settings."""
        # Just verify it accepts the parameter without error
        # (actual clearinghouse execution is tested via BasePipeline)
        from claim_validator.eligibility.models.request import EligibilityRequest
        from claim_validator.orchestrator import pre_claim_check

        request = EligibilityRequest(
            payer_id="00520",
            provider_npi="1245319599",
            subscriber_id="SUB123",
            subscriber_first_name="Alice",
            subscriber_last_name="Williams",
            subscriber_dob="1980-07-22",
            service_type_code="30",
        )
        # Pass clearinghouse_config — won't actually call clearinghouse
        # because EligibilityPipeline doesn't use BasePipeline yet
        result = pre_claim_check(
            request,
            clearinghouse_config={"provider": "stedi", "api_key": "test"},
        )
        assert result is not None

    def test_api_validate_accepts_clearinghouse_config(self) -> None:
        """validate() passes clearinghouse_config to settings."""
        from claim_validator._api import validate

        claim = {
            "claim_id": "CLM-001",
            "claim_type": "professional",
            "payer_id": "00520",
            "billing_provider_npi": "1234567890",
            "subscriber_id": "SUB123",
            "patient_first_name": "Alice",
            "patient_last_name": "Williams",
            "patient_date_of_birth": "1980-07-22",
            "total_charge_amount": 150.00,
            "service_date_from": "2026-02-20",
            "service_date_to": "2026-02-20",
            "diagnosis_codes": [{"code": "J06.9"}],
            "claim_lines": [
                {
                    "line_number": 1,
                    "cpt_code": "99213",
                    "charge_amount": 150.00,
                    "units": 1,
                    "service_date_from": "2026-02-20",
                    "service_date_to": "2026-02-20",
                }
            ],
        }
        # clearinghouse_config merges into settings but won't
        # execute because ValidationPipeline doesn't use BasePipeline yet
        result = validate(
            claim,
            clearinghouse_config={"provider": "stedi", "api_key": "test"},
        )
        assert isinstance(result, PipelineResult)

    def test_settings_model_copy_with_clearinghouse(self) -> None:
        """Settings.model_copy preserves clearinghouse_config."""
        settings = ClaimValidatorSettings()
        assert settings.clearinghouse_config is None

        updated = settings.model_copy(
            update={"clearinghouse_config": {"provider": "waystar", "api_key": "k"}}
        )
        assert updated.clearinghouse_config is not None
        assert updated.clearinghouse_config["provider"] == "waystar"


# ---------------------------------------------------------------------------
# AC-8: build_clearinghouse_client edge cases
# ---------------------------------------------------------------------------


class TestBuildClientEdgeCases:
    """Additional tests for the build helper."""

    def test_unknown_provider_raises(self) -> None:
        from claim_validator.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError, match="unknown_provider"):
            build_clearinghouse_client({"provider": "unknown_provider"})

    def test_builds_waystar_client(self) -> None:
        from claim_validator.clearinghouse.providers.waystar import WaystarClient

        client = build_clearinghouse_client(
            {"provider": "waystar", "api_key": "k", "secret": "s"}
        )
        assert isinstance(client, WaystarClient)
        assert client.provider_name == "waystar"
        client.close()

    def test_builds_claimmd_client(self) -> None:
        from claim_validator.clearinghouse.providers.claimmd import ClaimMDClient

        client = build_clearinghouse_client(
            {"provider": "claimmd", "api_key": "account-key-123"}
        )
        assert isinstance(client, ClaimMDClient)
        assert client.provider_name == "claimmd"
        client.close()
