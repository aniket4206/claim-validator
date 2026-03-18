"""Public API — process_claim() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.response import EligibilityResponse
from claim_validator.models.claim import ClaimData
from claim_validator.prior_auth.models.request import PriorAuthRequest
from claim_validator.workflow.models import FullWorkflowResult, WorkflowResult
from claim_validator.workflow.orchestrator import WorkflowOrchestrator
from claim_validator.workflow.stages import (
    ClaimValidationStage,
    EligibilityStage,
    PADeterminationStage,
    PriorAuthStage,
)
from claim_validator.workflow.stages_v2 import (
    AIClaimAnalysisStage,
    AIPreSubmissionStage,
    ClaimStatusStage,
    ClaimSubmissionStage,
    EligibilityGateStage,
    PriorAuthGateStage,
    RuleBasedClaimStage,
)


class ClaimRequest:
    """Container for all inputs to process_claim().

    Callers construct each domain model explicitly.  Dicts are coerced
    to the appropriate Pydantic model.
    """

    def __init__(
        self,
        *,
        eligibility_request: dict[str, Any] | EligibilityRequest,
        claim_data: dict[str, Any] | ClaimData,
        eligibility_response: EligibilityResponse | None = None,
        pa_request: dict[str, Any] | PriorAuthRequest | None = None,
    ) -> None:
        # Coerce dicts to models
        if isinstance(eligibility_request, dict):
            eligibility_request = EligibilityRequest(**eligibility_request)
        self.eligibility_request = eligibility_request

        if isinstance(claim_data, dict):
            claim_data = ClaimData(**claim_data)
        self.claim_data = claim_data

        self.eligibility_response = eligibility_response

        if isinstance(pa_request, dict):
            pa_request = PriorAuthRequest(**pa_request)
        self.pa_request = pa_request


def process_claim(
    request: ClaimRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    clearinghouse_config: dict[str, Any] | None = None,
) -> WorkflowResult:
    """Run the full claim workflow: Eligibility → PA → Claim Validation.

    Args:
        request: ClaimRequest with pre-built domain models.
        settings: Optional settings override.
        ai_config: Optional AI provider config dict.
        clearinghouse_config: Optional clearinghouse provider config dict.

    Returns:
        WorkflowResult with per-stage results.

    Raises:
        pydantic.ValidationError: If ClaimRequest is constructed with
            invalid dict data (coercion fails).
    """
    # Wire ai_config / clearinghouse_config into settings
    if ai_config is not None or clearinghouse_config is not None:
        updates: dict[str, Any] = {}
        if ai_config is not None:
            updates["ai_config"] = ai_config
        if clearinghouse_config is not None:
            updates["clearinghouse_config"] = clearinghouse_config

        if settings is not None:
            settings = settings.model_copy(update=updates)
        else:
            settings = ClaimValidatorSettings(**updates)

    stages = [
        EligibilityStage(settings=settings),
        PADeterminationStage(settings=settings),
        PriorAuthStage(settings=settings),
        ClaimValidationStage(settings=settings),
    ]

    input_data: dict[str, Any] = {
        "eligibility_request": request.eligibility_request,
        "eligibility_response": request.eligibility_response,
        "claim_data": request.claim_data,
        "pa_request": request.pa_request,
    }

    orchestrator = WorkflowOrchestrator(stages)
    return orchestrator.execute(input_data)


def process_claim_full(
    request: ClaimRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    clearinghouse_config: dict[str, Any] | None = None,
) -> FullWorkflowResult:
    """Run the full 7-stage claim pipeline: validate, check, submit.

    Cost-first ordering: free rule-based checks run before any paid
    API calls.  PA is rule-based only (no AI).

    Stage 1: Rule-Based Claim Validation   [GATE]
    Stage 2: AI Claim Analysis             [NON-GATE, optional]
    Stage 3: Eligibility (rules + clearinghouse) [GATE]
    Stage 4: Prior Authorization (rules + ClaimMD) [GATE]
    Stage 5: AI Pre-Submission Summary     [NON-GATE, optional]
    Stage 6: Claim Submission              [FINAL]
    Stage 7: Claim Status                  [INFORMATIONAL, optional]

    Args:
        request: ClaimRequest with pre-built domain models.
        settings: Optional settings override.
        ai_config: Optional AI provider config dict.
        clearinghouse_config: Optional clearinghouse provider config dict.

    Returns:
        FullWorkflowResult with per-stage results and submission status.
    """
    # Wire configs into settings
    if ai_config is not None or clearinghouse_config is not None:
        updates: dict[str, Any] = {}
        if ai_config is not None:
            updates["ai_config"] = ai_config
        if clearinghouse_config is not None:
            updates["clearinghouse_config"] = clearinghouse_config

        if settings is not None:
            settings = settings.model_copy(update=updates)
        else:
            settings = ClaimValidatorSettings(**updates)

    stages = [
        RuleBasedClaimStage(settings=settings),
        AIClaimAnalysisStage(settings=settings),
        EligibilityGateStage(settings=settings),
        PriorAuthGateStage(settings=settings),
        AIPreSubmissionStage(settings=settings),
        ClaimSubmissionStage(settings=settings),
        ClaimStatusStage(settings=settings),
    ]

    input_data: dict[str, Any] = {
        "eligibility_request": request.eligibility_request,
        "eligibility_response": request.eligibility_response,
        "claim_data": request.claim_data,
        "pa_request": request.pa_request,
    }

    wf_ctx: dict[str, Any] = {}
    orchestrator = WorkflowOrchestrator(stages)
    wf_result = orchestrator.execute(input_data, workflow_context=wf_ctx)

    return FullWorkflowResult(
        rule_based_claim=wf_ctx.get("rule_based_claim_result"),
        ai_claim_analysis=wf_ctx.get("ai_claim_result"),
        eligibility=wf_ctx.get("eligibility_result"),
        eligibility_rejection_summary=wf_ctx.get("eligibility_rejection_summary"),
        pa_determination=wf_ctx.get("pa_determination"),
        prior_auth=wf_ctx.get("prior_auth_result"),
        pa_submission=wf_ctx.get("pa_submission_result"),
        ai_pre_submission_summary=wf_ctx.get("ai_pre_submission_summary"),
        submission=wf_ctx.get("submission_result"),
        claim_status=wf_ctx.get("claim_status_result"),
        stopped_at=wf_result.stopped_at,
        stage_results=wf_result.stage_results,
        findings=wf_result.findings,
        execution_time=wf_result.execution_time,
    )
