"""Tests for V2 workflow stages — 7-stage cost-first pipeline."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.models.results import Finding, PhaseResult, PipelineResult, ValidatorOutput
from claim_validator.workflow.stages_v2 import (
    AIClaimAnalysisStage,
    AIPreSubmissionStage,
    ClaimStatusStage,
    ClaimSubmissionStage,
    EligibilityGateStage,
    PriorAuthGateStage,
    RuleBasedClaimStage,
)


def _make_pipeline_result(passed: bool = True) -> PipelineResult:
    findings = []
    if not passed:
        findings = [
            Finding(
                code="TEST_ERROR",
                message="test",
                severity=Severity.ERROR,
                field_name="test",
            )
        ]
    return PipelineResult(
        phase_results=[
            PhaseResult(phase="rule_based", validator_outputs=[], execution_time=0.01)
        ],
        execution_time=0.01,
    ) if passed else PipelineResult(
        phase_results=[
            PhaseResult(
                phase="rule_based",
                validator_outputs=[
                    MagicMock(findings=findings)
                ],
                execution_time=0.01,
            )
        ],
        execution_time=0.01,
    )


# ---------------------------------------------------------------------------
# Stage 1: RuleBasedClaimStage
# ---------------------------------------------------------------------------


class TestRuleBasedClaimStage:
    def test_name_and_gate(self) -> None:
        stage = RuleBasedClaimStage()
        assert stage.name == "rule_based_claim"
        assert stage.is_gate is True

    def test_never_skips(self) -> None:
        stage = RuleBasedClaimStage()
        skip, reason = stage.should_skip({})
        assert skip is False

    def test_missing_claim_data_fails(self) -> None:
        stage = RuleBasedClaimStage()
        result = stage.run({})
        assert result.passed is False
        assert result.findings[0].code == "CLAIM_MISSING_DATA"

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_runs_rule_based_only(self, mock_from_settings: MagicMock) -> None:
        mock_pipeline = MagicMock()
        mock_result = _make_pipeline_result(passed=True)
        mock_pipeline.run.return_value = mock_result
        mock_from_settings.return_value = mock_pipeline

        stage = RuleBasedClaimStage(settings=ClaimValidatorSettings())
        wf_ctx: dict[str, Any] = {}
        result = stage.run(
            {"claim_data": MagicMock()},
            workflow_context=wf_ctx,
        )

        assert result.passed is True
        assert result.stage_name == "rule_based_claim"
        assert "rule_based_claim_result" in wf_ctx


# ---------------------------------------------------------------------------
# Stage 2: AIClaimAnalysisStage
# ---------------------------------------------------------------------------


class TestAIClaimAnalysisStage:
    def test_name_and_not_gate(self) -> None:
        stage = AIClaimAnalysisStage()
        assert stage.name == "ai_claim_analysis"
        assert stage.is_gate is False

    def test_skips_without_settings(self) -> None:
        stage = AIClaimAnalysisStage()
        skip, reason = stage.should_skip({})
        assert skip is True

    def test_skips_without_ai_config(self) -> None:
        stage = AIClaimAnalysisStage(settings=ClaimValidatorSettings())
        skip, reason = stage.should_skip({})
        assert skip is True
        assert "No AI provider" in (reason or "")

    def test_skips_when_rule_based_failed(self) -> None:
        settings = ClaimValidatorSettings(
            ai_config={"provider": "groq", "api_key": "k", "model": "m"},
            ai_validators=["claim_validator.validators.ai.code_validation.CodeValidationAI"],
        )
        stage = AIClaimAnalysisStage(settings=settings)
        mock_result = MagicMock()
        mock_result.passed = False
        skip, reason = stage.should_skip(
            {"rule_based_claim_result": mock_result}
        )
        assert skip is True


# ---------------------------------------------------------------------------
# Stage 3: EligibilityGateStage
# ---------------------------------------------------------------------------


class TestEligibilityGateStage:
    def test_name_and_gate(self) -> None:
        stage = EligibilityGateStage()
        assert stage.name == "eligibility"
        assert stage.is_gate is True

    def test_never_skips(self) -> None:
        stage = EligibilityGateStage()
        skip, reason = stage.should_skip({})
        assert skip is False

    def test_missing_request_fails(self) -> None:
        stage = EligibilityGateStage()
        result = stage.run({})
        assert result.passed is False
        assert result.findings[0].code == "ELIG_MISSING_REQUEST"

    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_stores_result_in_context(
        self, mock_from_settings: MagicMock,
    ) -> None:
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.findings = []
        mock_pipeline.run.return_value = mock_result
        mock_from_settings.return_value = mock_pipeline

        stage = EligibilityGateStage()
        wf_ctx: dict[str, Any] = {}
        result = stage.run(
            {"eligibility_request": MagicMock()},
            workflow_context=wf_ctx,
        )

        assert result.passed is True
        assert "eligibility_result" in wf_ctx


# ---------------------------------------------------------------------------
# Stage 4: PriorAuthGateStage
# ---------------------------------------------------------------------------


class TestPriorAuthGateStage:
    def test_name_and_gate(self) -> None:
        stage = PriorAuthGateStage()
        assert stage.name == "prior_auth"
        assert stage.is_gate is True

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    def test_skips_when_not_required(
        self, mock_determine: MagicMock,
    ) -> None:
        mock_det = MagicMock()
        mock_det.required = False
        mock_determine.return_value = mock_det

        stage = PriorAuthGateStage()
        result = stage.run(
            {},
            workflow_context={},
        )

        assert result.passed is True
        assert result.skipped is True

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    def test_fails_when_required_but_no_request(
        self, mock_determine: MagicMock,
    ) -> None:
        mock_det = MagicMock()
        mock_det.required = True
        mock_determine.return_value = mock_det

        stage = PriorAuthGateStage()
        result = stage.run(
            {},
            workflow_context={},
        )

        assert result.passed is False
        assert result.findings[0].code == "PA_REQUIRED_NO_REQUEST"

    @patch("claim_validator.prior_auth.pipeline.PriorAuthPipeline.from_settings")
    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    def test_runs_rule_based_validation(
        self,
        mock_determine: MagicMock,
        mock_from_settings: MagicMock,
    ) -> None:
        mock_det = MagicMock()
        mock_det.required = True
        mock_determine.return_value = mock_det

        mock_pipeline = MagicMock()
        mock_pa_result = MagicMock()
        mock_pa_result.passed = True
        mock_pa_result.findings = []
        mock_pipeline.run.return_value = mock_pa_result
        mock_from_settings.return_value = mock_pipeline

        stage = PriorAuthGateStage(settings=ClaimValidatorSettings())
        wf_ctx: dict[str, Any] = {}
        result = stage.run(
            {"pa_request": MagicMock()},
            workflow_context=wf_ctx,
        )

        assert result.passed is True
        assert "prior_auth_result" in wf_ctx


# ---------------------------------------------------------------------------
# Stage 5: AIPreSubmissionStage
# ---------------------------------------------------------------------------


class TestAIPreSubmissionStage:
    def test_name_and_not_gate(self) -> None:
        stage = AIPreSubmissionStage()
        assert stage.name == "ai_pre_submission"
        assert stage.is_gate is False

    def test_skips_without_ai_config(self) -> None:
        stage = AIPreSubmissionStage()
        skip, reason = stage.should_skip({})
        assert skip is True

    def test_skips_with_empty_settings(self) -> None:
        stage = AIPreSubmissionStage(settings=ClaimValidatorSettings())
        skip, reason = stage.should_skip({})
        assert skip is True


# ---------------------------------------------------------------------------
# Stage 6: ClaimSubmissionStage
# ---------------------------------------------------------------------------


class TestClaimSubmissionStage:
    def test_name_and_not_gate(self) -> None:
        stage = ClaimSubmissionStage()
        assert stage.name == "claim_submission"
        assert stage.is_gate is False

    def test_skips_without_clearinghouse(self) -> None:
        stage = ClaimSubmissionStage()
        skip, reason = stage.should_skip({})
        assert skip is True

    def test_skips_with_empty_settings(self) -> None:
        stage = ClaimSubmissionStage(settings=ClaimValidatorSettings())
        skip, reason = stage.should_skip({})
        assert skip is True

    def test_missing_claim_data_fails(self) -> None:
        settings = ClaimValidatorSettings(
            clearinghouse_config={"provider": "claimmd", "api_key": "test"},
        )
        stage = ClaimSubmissionStage(settings=settings)
        result = stage.run({})
        assert result.passed is False
        assert result.findings[0].code == "SUBMISSION_MISSING_DATA"


# ---------------------------------------------------------------------------
# Stage 7: ClaimStatusStage
# ---------------------------------------------------------------------------


class TestClaimStatusStage:
    def test_name_and_not_gate(self) -> None:
        stage = ClaimStatusStage()
        assert stage.name == "claim_status"
        assert stage.is_gate is False

    def test_skips_without_submission(self) -> None:
        stage = ClaimStatusStage()
        skip, reason = stage.should_skip({})
        assert skip is True

    def test_skips_with_failed_submission(self) -> None:
        stage = ClaimStatusStage()
        mock_submission = MagicMock()
        mock_submission.accepted = False
        skip, reason = stage.should_skip({"submission_result": mock_submission})
        assert skip is True


# ---------------------------------------------------------------------------
# Integration: process_claim_full
# ---------------------------------------------------------------------------


class TestProcessClaimFull:
    def test_importable_from_top_level(self) -> None:
        from claim_validator import process_claim_full as fn
        assert callable(fn)

    def test_importable_from_workflow(self) -> None:
        from claim_validator.workflow import process_claim_full as fn
        assert callable(fn)

    def test_full_workflow_result_importable(self) -> None:
        from claim_validator import FullWorkflowResult
        assert FullWorkflowResult is not None

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_rule_based_gate_stops_on_failure(
        self, mock_from_settings: MagicMock,
    ) -> None:
        from claim_validator.workflow._api import ClaimRequest, process_claim_full

        # Make rule-based validation fail with an error finding
        fail_result = PipelineResult(
            phase_results=[
                PhaseResult(
                    phase="rule_based",
                    validator_outputs=[
                        ValidatorOutput(
                            validator_name="npi",
                            findings=[
                                Finding(
                                    code="INVALID_NPI",
                                    message="Bad NPI",
                                    severity=Severity.ERROR,
                                    field_name="billing_provider_npi",
                                )
                            ],
                        )
                    ],
                    execution_time=0.01,
                )
            ],
            execution_time=0.01,
        )
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = fail_result
        mock_from_settings.return_value = mock_pipeline

        # Use MagicMock to avoid Pydantic validation of test data
        mock_elig_req = MagicMock()
        mock_claim = MagicMock()
        request = ClaimRequest.__new__(ClaimRequest)
        request.eligibility_request = mock_elig_req
        request.claim_data = mock_claim
        request.eligibility_response = None
        request.pa_request = None

        result = process_claim_full(request)

        # Gate should stop at rule_based_claim
        assert result.stopped_at == "rule_based_claim"
        assert result.passed is False
        # Should NOT have progressed to eligibility
        assert result.eligibility is None
