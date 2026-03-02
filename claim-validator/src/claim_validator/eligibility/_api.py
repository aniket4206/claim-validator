"""Top-level check_eligibility() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.eligibility.pipeline import EligibilityPipeline


def check_eligibility(
    request: dict[str, Any] | EligibilityRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
) -> EligibilityResult:
    """Validate an eligibility request and return structured results.

    Args:
        request: Eligibility request as a dict or EligibilityRequest instance.
        settings: Optional settings. Uses defaults if None
            (all 6 rule-based validators, no AI).

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

    pipeline = EligibilityPipeline.from_settings(settings)
    return pipeline.run(request_model)
