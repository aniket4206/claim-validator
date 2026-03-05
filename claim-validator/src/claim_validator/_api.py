"""Top-level validate() convenience function."""

from __future__ import annotations

from typing import Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import PipelineResult
from claim_validator.validators.pipeline import ValidationPipeline


def validate(
    claim: dict[str, Any] | ClaimData,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    clearinghouse_config: dict[str, Any] | None = None,
) -> PipelineResult:
    """Validate a healthcare claim and return structured results.

    Args:
        claim: Claim data as a dict or ClaimData instance.
        settings: Optional settings. Uses defaults if None
            (all 8 rule-based validators, no AI).
        ai_config: Optional AI provider config dict.
            Keys: provider, api_key, model (+ provider-specific).
            Overrides settings.ai_config if both provided.
        clearinghouse_config: Optional clearinghouse provider config dict.
            Keys: ``provider`` (required), plus provider-specific keys
            (``api_key``, ``secret``, etc.). Overrides
            ``settings.clearinghouse_config`` when both provided.

    Returns:
        PipelineResult with findings from all validators.

    Raises:
        pydantic.ValidationError: If claim dict is malformed.
    """
    if isinstance(claim, dict):
        claim_data = ClaimData(**claim)
    elif isinstance(claim, ClaimData):
        claim_data = claim
    else:
        msg = (
            f"claim must be a dict or ClaimData, "
            f"got {type(claim).__name__}"
        )
        raise ValueError(msg)

    if ai_config is not None:
        if settings is not None:
            settings = settings.model_copy(
                update={"ai_config": ai_config},
            )
        else:
            settings = ClaimValidatorSettings(
                ai_config=ai_config,
            )

    if clearinghouse_config is not None:
        if settings is not None:
            settings = settings.model_copy(
                update={"clearinghouse_config": clearinghouse_config},
            )
        else:
            settings = ClaimValidatorSettings(
                clearinghouse_config=clearinghouse_config,
            )

    pipeline = ValidationPipeline.from_settings(settings)
    return pipeline.run(claim_data)
