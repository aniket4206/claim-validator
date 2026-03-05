"""Tests for Stage protocol and concrete stage implementations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from claim_validator.prior_auth.models.result import PADeterminationResult
from claim_validator.workflow.models import StageResult
from claim_validator.workflow.stages import (
    ClaimValidationStage,
    EligibilityStage,
    PADeterminationStage,
    PriorAuthStage,
    Stage,
)


class TestStageProtocol:
    """Stage protocol compliance tests."""

    def test_eligibility_stage_is_stage(self):
        assert isinstance(EligibilityStage(), Stage)

    def test_pa_determination_stage_is_stage(self):
        assert isinstance(PADeterminationStage(), Stage)

    def test_prior_auth_stage_is_stage(self):
        assert isinstance(PriorAuthStage(), Stage)

    def test_claim_validation_stage_is_stage(self):
        assert isinstance(ClaimValidationStage(), Stage)


class TestEligibilityStage:
    """EligibilityStage tests."""

    def test_name_and_gate(self):
        stage = EligibilityStage()
        assert stage.name == "eligibility"
        assert stage.is_gate is True

    def test_never_skips(self):
        stage = EligibilityStage()
        skip, reason = stage.should_skip({})
        assert skip is False
        assert reason is None

    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_run_delegates_to_pipeline(self, mock_from_settings: MagicMock):
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.findings = []
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_from_settings.return_value = mock_pipeline

        stage = EligibilityStage()
        request = MagicMock()
        response = MagicMock()
        input_data = {"eligibility_request": request, "eligibility_response": response}
        wf_ctx: dict[str, Any] = {}

        result = stage.run(input_data, workflow_context=wf_ctx)

        mock_pipeline.run.assert_called_once_with(
            request, response=response, validation_context=None,
        )
        assert result.stage_name == "eligibility"
        assert result.passed is True
        assert wf_ctx["eligibility_result"] == mock_result
        assert wf_ctx["eligibility_response"] == response

    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_run_returns_stage_result(self, mock_from_settings: MagicMock):
        from claim_validator.constants import Severity
        from claim_validator.models.results import Finding

        err_finding = Finding(
            code="TEST_ERR", message="fail", severity=Severity.ERROR, field_name="x",
        )
        mock_result = MagicMock()
        mock_result.passed = False
        mock_result.findings = [err_finding]
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_from_settings.return_value = mock_pipeline

        stage = EligibilityStage()
        result = stage.run({"eligibility_request": MagicMock(), "eligibility_response": None})

        assert isinstance(result, StageResult)
        assert result.passed is False
        assert result.execution_time > 0


class TestPADeterminationStage:
    """PADeterminationStage tests."""

    def test_name_and_not_gate(self):
        stage = PADeterminationStage()
        assert stage.name == "pa_determination"
        assert stage.is_gate is False

    def test_skip_when_no_response(self):
        stage = PADeterminationStage()
        skip, reason = stage.should_skip({})
        assert skip is True
        assert "No eligibility response" in reason

    def test_no_skip_when_response_available(self):
        stage = PADeterminationStage()
        skip, reason = stage.should_skip({"eligibility_response": MagicMock()})
        assert skip is False
        assert reason is None

    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    def test_run_stores_determination(self, mock_determine: MagicMock):
        pa_det = PADeterminationResult(
            required=False, confidence="high", reason="No PA required",
        )
        mock_determine.return_value = pa_det

        stage = PADeterminationStage()
        wf_ctx: dict[str, Any] = {"eligibility_response": MagicMock(raw_response={})}
        result = stage.run({}, workflow_context=wf_ctx)

        assert result.stage_name == "pa_determination"
        assert result.passed is True
        assert wf_ctx["pa_determination"] == pa_det
        assert result.detail == pa_det


class TestPriorAuthStage:
    """PriorAuthStage tests."""

    def test_name_and_gate(self):
        stage = PriorAuthStage()
        assert stage.name == "prior_auth"
        assert stage.is_gate is True

    def test_skip_when_pa_not_required(self):
        stage = PriorAuthStage()
        pa_det = PADeterminationResult(
            required=False, confidence="high", reason="Not required",
        )
        skip, reason = stage.should_skip({"pa_determination": pa_det})
        assert skip is True
        assert "not required" in reason

    def test_skip_when_no_determination(self):
        stage = PriorAuthStage()
        skip, reason = stage.should_skip({})
        assert skip is True

    def test_no_skip_when_required(self):
        stage = PriorAuthStage()
        pa_det = PADeterminationResult(
            required=True, confidence="high", reason="Required",
        )
        skip, reason = stage.should_skip({"pa_determination": pa_det})
        assert skip is False
        assert reason is None

    def test_run_no_pa_request_returns_warning(self):
        stage = PriorAuthStage()
        result = stage.run({"pa_request": None})
        assert result.passed is False
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_REQUIRED"

    @patch("claim_validator.prior_auth.pipeline.PriorAuthPipeline.from_settings")
    def test_run_delegates_to_pipeline(self, mock_from_settings: MagicMock):
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.findings = []
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_from_settings.return_value = mock_pipeline

        stage = PriorAuthStage()
        pa_request = MagicMock()
        wf_ctx: dict[str, Any] = {}
        result = stage.run({"pa_request": pa_request}, workflow_context=wf_ctx)

        mock_pipeline.run.assert_called_once_with(
            pa_request, validation_context=None,
        )
        assert result.passed is True
        assert wf_ctx["prior_auth_result"] == mock_result


class TestClaimValidationStage:
    """ClaimValidationStage tests."""

    def test_name_and_not_gate(self):
        stage = ClaimValidationStage()
        assert stage.name == "claim_validation"
        assert stage.is_gate is False

    def test_never_skips(self):
        stage = ClaimValidationStage()
        skip, reason = stage.should_skip({})
        assert skip is False
        assert reason is None

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    def test_run_delegates_to_pipeline(self, mock_from_settings: MagicMock):
        mock_result = MagicMock()
        mock_result.passed = True
        mock_result.findings = []
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_from_settings.return_value = mock_pipeline

        stage = ClaimValidationStage()
        claim_data = MagicMock()
        wf_ctx: dict[str, Any] = {}
        result = stage.run({"claim_data": claim_data}, workflow_context=wf_ctx)

        mock_pipeline.run.assert_called_once_with(
            claim_data, validation_context=None,
        )
        assert result.passed is True
        assert wf_ctx["claim_validation_result"] == mock_result
