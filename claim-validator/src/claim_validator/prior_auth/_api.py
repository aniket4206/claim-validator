"""Top-level submit_prior_auth() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.prior_auth.models.request import PriorAuthRequest
from claim_validator.prior_auth.models.result import PriorAuthResult
from claim_validator.prior_auth.pipeline import PriorAuthPipeline


def submit_prior_auth(
    request: dict[str, Any] | PriorAuthRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
) -> PriorAuthResult:
    """Validate a prior authorization request and return structured results.

    Args:
        request: PA request as a dict or PriorAuthRequest instance.
        settings: Optional settings. Uses defaults if None
            (all 7 rule-based validators, no clearinghouse, no AI).

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

    pipeline = PriorAuthPipeline.from_settings(settings)
    return pipeline.run(request_model)
