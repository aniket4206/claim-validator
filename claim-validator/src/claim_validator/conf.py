"""Configuration for claim-validator library."""

from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default 8 rule-based validators (dotted paths)
DEFAULT_RULE_VALIDATORS: list[str] = [
    "claim_validator.validators.rule_based.completeness.CompletenessValidator",
    "claim_validator.validators.rule_based.npi.NPIValidator",
    "claim_validator.validators.rule_based.subscriber_id.SubscriberIDValidator",
    "claim_validator.validators.rule_based.demographics.DemographicsValidator",
    "claim_validator.validators.rule_based.coding.CodingValidator",
    "claim_validator.validators.rule_based.monetary.MonetaryValidator",
    "claim_validator.validators.rule_based.duplicate.DuplicateValidator",
    "claim_validator.validators.rule_based.timely_filing.TimelyFilingValidator",
]


class ClaimValidatorSettings(BaseSettings):
    """Configuration for the claim-validator library.

    Reads from environment variables with ``CLAIM_VALIDATOR_`` prefix.
    All fields have sensible defaults for zero-config rule-based validation.
    """

    model_config = SettingsConfigDict(
        env_prefix="CLAIM_VALIDATOR_",
        frozen=True,
    )

    rule_validators: list[str] = DEFAULT_RULE_VALIDATORS
    ai_validators: list[str] = []
    skip_ai_on_rule_failure: bool = True
    ai_config: dict[str, Any] | None = None
