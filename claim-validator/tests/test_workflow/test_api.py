"""Tests for process_claim() API and ClaimRequest."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, PipelineResult
from claim_validator.prior_auth.models.request import PriorAuthRequest
from claim_validator.workflow._api import ClaimRequest, process_claim
from claim_validator.workflow.models import WorkflowResult


def _make_eligibility_dict() -> dict[str, Any]:
    return {
        "provider_npi": "1234567890",
        "payer_id": "60054",
        "subscriber_id": "ABC123",
        "subscriber_first_name": "John",
        "subscriber_last_name": "Doe",
        "subscriber_dob": "1985-01-15",
    }


def _make_claim_dict() -> dict[str, Any]:
    return {
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
    }


def _elig_result(findings: list[Finding] | None = None) -> EligibilityResult:
    return EligibilityResult(findings=findings or [])


def _pipeline_result() -> PipelineResult:
    return PipelineResult()


class TestClaimRequest:
    """ClaimRequest container tests."""

    def test_accepts_model_instances(self):
        elig = EligibilityRequest(**_make_eligibility_dict())
        claim = ClaimData(**_make_claim_dict())
        req = ClaimRequest(eligibility_request=elig, claim_data=claim)

        assert isinstance(req.eligibility_request, EligibilityRequest)
        assert isinstance(req.claim_data, ClaimData)
        assert req.eligibility_response is None
        assert req.pa_request is None

    def test_coerces_dicts_to_models(self):
        req = ClaimRequest(
            eligibility_request=_make_eligibility_dict(),
            claim_data=_make_claim_dict(),
        )
        assert isinstance(req.eligibility_request, EligibilityRequest)
        assert isinstance(req.claim_data, ClaimData)

    def test_optional_pa_request_coercion(self):
        pa_dict: dict[str, Any] = {
            "requester_npi": "1234567890",
            "payer_id": "60054",
            "subscriber": {
                "member_id": "ABC123",
                "first_name": "John",
                "last_name": "Doe",
                "dob": "1985-01-15",
            },
            "service_lines": [
                {
                    "cpt_code": "27447",
                    "quantity": 1,
                },
            ],
        }
        req = ClaimRequest(
            eligibility_request=_make_eligibility_dict(),
            claim_data=_make_claim_dict(),
            pa_request=pa_dict,
        )
        assert isinstance(req.pa_request, PriorAuthRequest)


class TestProcessClaim:
    """process_claim() integration tests (mocked domain pipelines)."""

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_full_workflow_all_pass(
        self,
        mock_elig_from: MagicMock,
        mock_pa_det: MagicMock,
        mock_claim_from: MagicMock,
    ):
        # Eligibility passes — use real EligibilityResult
        elig_result = _elig_result()
        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = elig_result
        mock_elig_from.return_value = mock_elig_pipeline

        # PA not required (no eligibility_response → PADeterminationStage skipped)

        # Claim validation passes — use real PipelineResult
        claim_result = _pipeline_result()
        mock_claim_pipeline = MagicMock()
        mock_claim_pipeline.run.return_value = claim_result
        mock_claim_from.return_value = mock_claim_pipeline

        req = ClaimRequest(
            eligibility_request=_make_eligibility_dict(),
            claim_data=_make_claim_dict(),
        )
        result = process_claim(req)

        assert isinstance(result, WorkflowResult)
        assert result.stopped_at is None
        # 4 stage results: elig, pa_det(skipped), prior_auth(skipped), claim
        assert len(result.stage_results) == 4
        assert result.stage_results[1].skipped is True  # pa_determination
        assert result.stage_results[2].skipped is True  # prior_auth

    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_eligibility_gate_stops_workflow(self, mock_elig_from: MagicMock):
        err = Finding(
            code="ELIG_FAIL", message="Inactive coverage",
            severity=Severity.ERROR, field_name="coverage",
        )
        elig_result = _elig_result(findings=[err])
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = elig_result
        mock_elig_from.return_value = mock_pipeline

        req = ClaimRequest(
            eligibility_request=_make_eligibility_dict(),
            claim_data=_make_claim_dict(),
        )
        result = process_claim(req)

        assert result.stopped_at == "eligibility"
        assert len(result.findings) == 1
        assert result.findings[0].code == "ELIG_FAIL"

    @patch("claim_validator.validators.pipeline.ValidationPipeline.from_settings")
    @patch("claim_validator.prior_auth.determination.determine_pa_required")
    @patch("claim_validator.eligibility.pipeline.EligibilityPipeline.from_settings")
    def test_returns_workflow_result_type(
        self,
        mock_elig_from: MagicMock,
        mock_pa_det: MagicMock,
        mock_claim_from: MagicMock,
    ):
        # Use real domain results to pass Pydantic validation
        mock_elig_pipeline = MagicMock()
        mock_elig_pipeline.run.return_value = _elig_result()
        mock_elig_from.return_value = mock_elig_pipeline

        mock_claim_pipeline = MagicMock()
        mock_claim_pipeline.run.return_value = _pipeline_result()
        mock_claim_from.return_value = mock_claim_pipeline

        req = ClaimRequest(
            eligibility_request=_make_eligibility_dict(),
            claim_data=_make_claim_dict(),
        )
        result = process_claim(req)

        assert isinstance(result, WorkflowResult)
        assert result.execution_time > 0
