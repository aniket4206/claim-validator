"""Integration tests for process_claim_full() — 7-stage pipeline end-to-end.

Tests the full pipeline with mocked pipelines and clearinghouses to verify
stage ordering, gate logic, skip logic, and result assembly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import (
    Finding,
    PhaseResult,
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.prior_auth.models.result import PADeterminationResult
from claim_validator.workflow._api import ClaimRequest, process_claim_full
from claim_validator.workflow.models import FullWorkflowResult


def _make_elig_result(passed: bool = True) -> EligibilityResult:
    findings = []
    if not passed:
        findings = [
            Finding(
                code="ELIG_NOT_ACTIVE",
                message="Patient not eligible",
                severity=Severity.ERROR,
                field_name="eligibility",
            )
        ]
    return EligibilityResult(
        eligible=passed,
        findings=findings,
    )


def _make_pa_determination(required: bool = False) -> PADeterminationResult:
    return PADeterminationResult(
        required=required,
        confidence="high",
        reason="test",
    )


def _mock_request() -> ClaimRequest:
    """Build a ClaimRequest with MagicMock data to bypass Pydantic validation."""
    req = ClaimRequest.__new__(ClaimRequest)
    req.eligibility_request = MagicMock()
    req.claim_data = MagicMock()
    req.eligibility_response = None
    req.pa_request = None
    return req


def _passing_pipeline_result() -> PipelineResult:
    return PipelineResult(
        phase_results=[
            PhaseResult(phase="rule_based", validator_outputs=[], execution_time=0.01)
        ],
        execution_time=0.01,
    )


def _failing_pipeline_result(code: str = "TEST_ERROR", msg: str = "fail") -> PipelineResult:
    return PipelineResult(
        phase_results=[
            PhaseResult(
                phase="rule_based",
                validator_outputs=[
                    ValidatorOutput(
                        validator_name="test",
                        findings=[
                            Finding(
                                code=code,
                                message=msg,
                                severity=Severity.ERROR,
                                field_name="test",
                            )
                        ],
                    )
                ],
                execution_time=0.01,
            )
        ],
        execution_time=0.01,
    )


class TestProcessClaimFullGateLogic:
    """Test that gate stages stop the pipeline on failure."""

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_rule_based_gate_stops_pipeline(
        self, mock_from_settings: MagicMock,
    ) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = _failing_pipeline_result("INVALID_NPI", "Bad NPI")
        mock_from_settings.return_value = mock_pipeline

        result = process_claim_full(_mock_request())

        assert isinstance(result, FullWorkflowResult)
        assert result.stopped_at == "rule_based_claim"
        assert result.passed is False
        assert result.eligibility is None  # Never reached

    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_eligibility_gate_stops_pipeline(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
    ) -> None:
        # Rule-based passes
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = _passing_pipeline_result()
        mock_val_from.return_value = mock_val_pipeline

        # Eligibility fails
        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=False)
        mock_elig_from.return_value = mock_elig_pipeline

        result = process_claim_full(_mock_request())

        assert result.stopped_at == "eligibility"
        assert result.passed is False
        assert result.eligibility is not None  # Eligibility ran
        assert result.prior_auth is None  # Never reached


class TestProcessClaimFullSkipLogic:
    """Test that stages skip correctly."""

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_pa_skipped_when_not_required(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
        mock_determine: MagicMock,
    ) -> None:
        # Rule-based passes
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = _passing_pipeline_result()
        mock_val_from.return_value = mock_val_pipeline

        # Eligibility passes
        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=True)
        mock_elig_from.return_value = mock_elig_pipeline

        # PA not required
        mock_determine.return_value = _make_pa_determination(required=False)

        result = process_claim_full(_mock_request())

        # Pipeline should NOT stop at PA (it's skipped)
        assert result.stopped_at is None or result.stopped_at != "prior_auth"
        # PA determination should be in context
        assert result.pa_determination is not None
        assert result.pa_determination.required is False

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_ai_stages_skipped_without_ai_config(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
        mock_determine: MagicMock,
    ) -> None:
        # All rule-based passes
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = _passing_pipeline_result()
        mock_val_from.return_value = mock_val_pipeline

        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=True)
        mock_elig_from.return_value = mock_elig_pipeline

        mock_determine.return_value = _make_pa_determination(required=False)

        # No AI config, no clearinghouse config
        result = process_claim_full(_mock_request())

        # AI stages should be skipped
        stage_names = [sr.stage_name for sr in result.stage_results]
        assert "ai_claim_analysis" in stage_names
        assert "ai_pre_submission" in stage_names

        ai_stage = next(
            sr for sr in result.stage_results if sr.stage_name == "ai_claim_analysis"
        )
        assert ai_stage.skipped is True

        pre_sub = next(
            sr for sr in result.stage_results if sr.stage_name == "ai_pre_submission"
        )
        assert pre_sub.skipped is True


class TestProcessClaimFullHappyPath:
    """Test successful run through the pipeline."""

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_happy_path_no_ai_no_clearinghouse(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
        mock_determine: MagicMock,
    ) -> None:
        """Full pipeline: rule-based pass, elig pass, PA not required, no AI, no submission."""
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = _passing_pipeline_result()
        mock_val_from.return_value = mock_val_pipeline

        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=True)
        mock_elig_from.return_value = mock_elig_pipeline

        mock_determine.return_value = _make_pa_determination(required=False)

        result = process_claim_full(_mock_request())

        assert isinstance(result, FullWorkflowResult)
        assert result.passed is True
        assert result.stopped_at is None
        assert result.submitted is False  # No clearinghouse configured
        assert result.execution_time > 0

        # Verify all 7 stages ran/skipped
        stage_names = [sr.stage_name for sr in result.stage_results]
        assert "rule_based_claim" in stage_names
        assert "ai_claim_analysis" in stage_names
        assert "eligibility" in stage_names
        assert "prior_auth" in stage_names
        assert "ai_pre_submission" in stage_names
        assert "claim_submission" in stage_names
        assert "claim_status" in stage_names

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_stage_results_have_execution_times(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
        mock_determine: MagicMock,
    ) -> None:
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = _passing_pipeline_result()
        mock_val_from.return_value = mock_val_pipeline

        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=True)
        mock_elig_from.return_value = mock_elig_pipeline

        mock_determine.return_value = _make_pa_determination(required=False)

        result = process_claim_full(_mock_request())

        times = result.stage_times
        assert len(times) == 7
        assert all(isinstance(v, float) for v in times.values())

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_findings_aggregated_across_stages(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
        mock_determine: MagicMock,
    ) -> None:
        # Rule-based passes but with a warning
        warning_result = PipelineResult(
            phase_results=[
                PhaseResult(
                    phase="rule_based",
                    validator_outputs=[
                        ValidatorOutput(
                            validator_name="timely_filing",
                            findings=[
                                Finding(
                                    code="APPROACHING_DEADLINE",
                                    message="15 days left",
                                    severity=Severity.WARNING,
                                    field_name="filing_date",
                                )
                            ],
                        )
                    ],
                    execution_time=0.01,
                )
            ],
            execution_time=0.01,
        )
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = warning_result
        mock_val_from.return_value = mock_val_pipeline

        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=True)
        mock_elig_from.return_value = mock_elig_pipeline

        mock_determine.return_value = _make_pa_determination(required=False)

        result = process_claim_full(_mock_request())

        assert result.passed is True  # Warnings don't fail
        assert len(result.findings) >= 1
        assert any(f.code == "APPROACHING_DEADLINE" for f in result.findings)


class TestProcessClaimFullWithClearinghouse:
    """Test pipeline with mocked clearinghouse submission."""

    @patch("claim_validator.clearinghouse.build_clearinghouse_client")
    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_claim_submission_stage_runs(
        self,
        mock_val_from: MagicMock,
        mock_elig_from: MagicMock,
        mock_determine: MagicMock,
        mock_build_ch: MagicMock,
    ) -> None:
        # All stages pass
        mock_val_pipeline = MagicMock()
        mock_val_pipeline.run.return_value = _passing_pipeline_result()
        mock_val_from.return_value = mock_val_pipeline

        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _make_elig_result(passed=True)
        mock_elig_from.return_value = mock_elig_pipeline

        mock_determine.return_value = _make_pa_determination(required=False)

        # Mock clearinghouse
        mock_ch = MagicMock()
        mock_submission = MagicMock()
        mock_submission.accepted = True
        mock_submission.reference_id = "REF-123"
        mock_submission.status = "accepted"
        mock_ch.submit_claim.return_value = mock_submission
        mock_build_ch.return_value = mock_ch

        settings = ClaimValidatorSettings(
            clearinghouse_config={"provider": "claimmd", "api_key": "test"},
        )
        result = process_claim_full(_mock_request(), settings=settings)

        assert result.passed is True
        assert result.submitted is True
        assert result.submission is not None
        assert result.submission.accepted is True

        # Verify claim was submitted
        sub_stage = next(
            sr for sr in result.stage_results if sr.stage_name == "claim_submission"
        )
        assert sub_stage.skipped is False
