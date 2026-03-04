"""Integration tests for validation passthrough across workflow stages."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import PipelineResult
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.workflow._api import ClaimRequest, process_claim
from claim_validator.workflow.orchestrator import WorkflowOrchestrator
from claim_validator.workflow.stages import (
    ClaimValidationStage,
    EligibilityStage,
)


class TestPassthroughIntegration:
    """Verify ValidationContext flows through orchestrator → stages → pipelines."""

    def test_orchestrator_creates_validation_context(self):
        """Orchestrator should create a ValidationContext and pass to stages."""
        captured_ctx: list[ValidationContext | None] = []

        class _CapturingStage:
            name = "capture"
            is_gate = False

            def should_skip(self, context: dict[str, Any]) -> tuple[bool, str | None]:
                return False, None

            def run(
                self, input_data: Any, *,
                validation_context: ValidationContext | None = None,
                workflow_context: dict[str, Any] | None = None,
            ):
                captured_ctx.append(validation_context)
                from claim_validator.workflow.models import StageResult
                return StageResult(stage_name="capture", passed=True)

        orch = WorkflowOrchestrator([_CapturingStage()])
        orch.execute({})

        assert len(captured_ctx) == 1
        assert isinstance(captured_ctx[0], ValidationContext)

    def test_same_context_shared_across_stages(self):
        """All stages should receive the same ValidationContext instance."""
        captured: list[ValidationContext | None] = []

        class _CapturingStage:
            def __init__(self, name: str) -> None:
                self.name = name
                self.is_gate = False

            def should_skip(self, context: dict[str, Any]) -> tuple[bool, str | None]:
                return False, None

            def run(
                self, input_data: Any, *,
                validation_context: ValidationContext | None = None,
                workflow_context: dict[str, Any] | None = None,
            ):
                captured.append(validation_context)
                from claim_validator.workflow.models import StageResult
                return StageResult(stage_name=self.name, passed=True)

        orch = WorkflowOrchestrator([
            _CapturingStage("s1"),
            _CapturingStage("s2"),
        ])
        orch.execute({})

        assert len(captured) == 2
        assert captured[0] is captured[1]

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_stages_forward_context_to_pipelines(
        self,
        mock_elig_from: MagicMock,
        mock_claim_from: MagicMock,
    ):
        """EligibilityStage and ClaimValidationStage forward validation_context."""
        elig_result = EligibilityResult()
        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = elig_result
        mock_elig_from.return_value = mock_elig_pipeline

        claim_result = PipelineResult()
        mock_claim_pipeline = MagicMock()
        mock_claim_pipeline.run.return_value = claim_result
        mock_claim_from.return_value = mock_claim_pipeline

        ctx = ValidationContext()
        elig_stage = EligibilityStage()
        claim_stage = ClaimValidationStage()

        elig_stage.run(
            {"eligibility_request": MagicMock(), "eligibility_response": None},
            validation_context=ctx,
        )
        claim_stage.run(
            {"claim_data": MagicMock()},
            validation_context=ctx,
        )

        # Verify validation_context was forwarded to domain pipelines
        _, elig_kwargs = mock_elig_pipeline.run.call_args
        assert elig_kwargs["validation_context"] is ctx

        _, claim_kwargs = mock_claim_pipeline.run.call_args
        assert claim_kwargs["validation_context"] is ctx

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_process_claim_uses_passthrough(
        self,
        mock_elig_from: MagicMock,
        mock_claim_from: MagicMock,
    ):
        """process_claim() should wire passthrough end-to-end."""
        elig_result = EligibilityResult()
        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = elig_result
        mock_elig_from.return_value = mock_elig_pipeline

        claim_result = PipelineResult()
        mock_claim_pipeline = MagicMock()
        mock_claim_pipeline.run.return_value = claim_result
        mock_claim_from.return_value = mock_claim_pipeline

        req = ClaimRequest(
            eligibility_request={
                "provider_npi": "1234567890",
                "payer_id": "60054",
                "subscriber_id": "ABC123",
                "subscriber_first_name": "John",
                "subscriber_last_name": "Doe",
                "subscriber_dob": "1985-01-15",
            },
            claim_data={
                "claim_type": "professional",
                "billing_provider_npi": "1234567890",
                "payer_id": "60054",
                "subscriber_id": "ABC123",
                "patient_first_name": "John",
                "patient_last_name": "Doe",
                "patient_dob": "1985-01-15",
                "patient_gender": "M",
                "service_date": "2026-01-15",
                "diagnosis_codes": [{"code": "J06.9"}],
                "service_lines": [
                    {
                        "procedure_code": "99213",
                        "charge_amount": 150.0,
                        "units": 1.0,
                        "diagnosis_pointers": [1],
                    },
                ],
            },
        )
        process_claim(req)

        # Both pipelines should have received a ValidationContext
        _, elig_kwargs = mock_elig_pipeline.run.call_args
        assert isinstance(elig_kwargs["validation_context"], ValidationContext)

        _, claim_kwargs = mock_claim_pipeline.run.call_args
        assert isinstance(claim_kwargs["validation_context"], ValidationContext)

        # Same context instance
        assert elig_kwargs["validation_context"] is claim_kwargs["validation_context"]
