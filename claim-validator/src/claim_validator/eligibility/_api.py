"""Top-level check_eligibility() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.response import EligibilityResponse
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.eligibility.pipeline import EligibilityPipeline


def check_eligibility(
    request: dict[str, Any] | EligibilityRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    response: EligibilityResponse | None = None,
) -> EligibilityResult:
    """Validate an eligibility request and return structured results.

    Args:
        request: Eligibility request as a dict or EligibilityRequest instance.
        settings: Optional settings. Uses defaults if None
            (all 6 rule-based validators, no AI).
        ai_config: Optional AI provider config dict. Keys:
            ``provider``, ``api_key``, ``model``, plus provider extras.
            Overrides settings.ai_config if both provided.
        response: Optional pre-fetched EligibilityResponse for
            AI interpretation. When provided and AI is configured,
            the pipeline de-identifies and interprets the response.

    Returns:
        EligibilityResult with findings from all validators.

    Raises:
        ValueError: If request is not a dict or EligibilityRequest.
        pydantic.ValidationError: If request dict is malformed.
    """
    if isinstance(request, dict):
        request_model = EligibilityRequest(**request)
    elif isinstance(request, EligibilityRequest):
        request_model = request
    else:
        msg = (
            f"request must be a dict or EligibilityRequest, "
            f"got {type(request).__name__}"
        )
        raise ValueError(msg)

    # Wire ai_config into settings (mirror claims module pattern)
    if ai_config is not None:
        if settings is not None:
            settings = settings.model_copy(
                update={"ai_config": ai_config},
            )
        else:
            settings = ClaimValidatorSettings(ai_config=ai_config)

    pipeline = EligibilityPipeline.from_settings(settings)
    return pipeline.run(request_model, response=response)
