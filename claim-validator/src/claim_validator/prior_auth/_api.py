"""Top-level submit_prior_auth() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.prior_auth.models.request import PriorAuthRequest
from claim_validator.prior_auth.models.response import PriorAuthResponse
from claim_validator.prior_auth.models.result import PriorAuthResult
from claim_validator.prior_auth.pipeline import PriorAuthPipeline


def submit_prior_auth(
    request: dict[str, Any] | PriorAuthRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    response: PriorAuthResponse | None = None,
) -> PriorAuthResult:
    """Validate a prior authorization request and return structured results.

    Args:
        request: PA request as a dict or PriorAuthRequest instance.
        settings: Optional settings. Uses defaults if None
            (all 7 rule-based validators, no AI).
        ai_config: Optional AI provider config dict. Keys:
            ``provider``, ``api_key``, ``model``, plus provider extras.
            Overrides settings.ai_config if both provided.
        response: Optional pre-fetched PriorAuthResponse for
            AI interpretation. When provided and AI is configured,
            the pipeline de-identifies and interprets the response.

    Returns:
        PriorAuthResult with findings from all validators.

    Raises:
        ValueError: If request is not a dict or PriorAuthRequest.
        pydantic.ValidationError: If request dict is malformed.
    """
    if isinstance(request, dict):
        request_model = PriorAuthRequest(**request)
    elif isinstance(request, PriorAuthRequest):
        request_model = request
    else:
        msg = (
            f"request must be a dict or PriorAuthRequest, "
            f"got {type(request).__name__}"
        )
        raise ValueError(msg)

    # Wire ai_config into settings (mirror eligibility module pattern)
    if ai_config is not None:
        if settings is not None:
            settings = settings.model_copy(
                update={"ai_config": ai_config},
            )
        else:
            settings = ClaimValidatorSettings(ai_config=ai_config)

    pipeline = PriorAuthPipeline.from_settings(settings)
    return pipeline.run(request_model, response=response)
