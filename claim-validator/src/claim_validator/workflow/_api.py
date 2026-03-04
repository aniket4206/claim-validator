"""Public API — process_claim() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.response import EligibilityResponse
from claim_validator.models.claim import ClaimData
from claim_validator.prior_auth.models.request import PriorAuthRequest
from claim_validator.workflow.models import WorkflowResult
from claim_validator.workflow.orchestrator import WorkflowOrchestrator
from claim_validator.workflow.stages import (
    ClaimValidationStage,
    EligibilityStage,
    PADeterminationStage,
    PriorAuthStage,
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
