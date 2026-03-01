"""Configuration for claim-validator library."""

from __future__ import annotations

from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# Default PA rule-based validators
DEFAULT_PA_RULE_VALIDATORS: list[str] = [
    "claim_validator.prior_auth.validators.rule_based.cross_field.PACrossFieldValidator",
    "claim_validator.prior_auth.validators.rule_based.date_of_birth.PADateOfBirthValidator",
    "claim_validator.prior_auth.validators.rule_based.diagnosis.PADiagnosisValidator",
    "claim_validator.prior_auth.validators.rule_based.member_id.PAMemberIDValidator",
    "claim_validator.prior_auth.validators.rule_based.npi.PANPIValidator",
    "claim_validator.prior_auth.validators.rule_based.procedure.PAProcedureValidator",
    "claim_validator.prior_auth.validators.rule_based.service_date.PAServiceDateValidator",
]

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

    # Prior authorization settings
    pa_rule_validators: list[str] = DEFAULT_PA_RULE_VALIDATORS
    pa_ai_validators: list[str] = []
    skip_clearinghouse_on_pa_failure: bool = True
    pa_skip_ai: bool = False

    # Eligibility settings
    stedi_api_key: str | None = None
    stedi_environment: str = "sandbox"
    eligibility_rule_validators: list[str] = []
    eligibility_ai_validators: list[str] = []
    skip_clearinghouse_on_eligibility_failure: bool = True
    eligibility_skip_ai: bool = False
