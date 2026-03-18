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


# Default eligibility AI validators
DEFAULT_ELIG_AI_VALIDATORS: list[str] = [
    "claim_validator.eligibility.validators.ai.interpreter.EligibilityInterpreterAI",
]

# Default PA AI validators
DEFAULT_PA_AI_VALIDATORS: list[str] = [
    "claim_validator.prior_auth.validators.ai.interpreter.PriorAuthInterpreterAI",
]


# Default eligibility rule-based validators
DEFAULT_ELIG_RULE_VALIDATORS: list[str] = [
    "claim_validator.eligibility.validators.rule_based.date.EligibilityDateValidator",
    "claim_validator.eligibility.validators.rule_based.demographics.EligibilityDemographicsValidator",
    "claim_validator.eligibility.validators.rule_based.member_id.MemberIDValidator",
    "claim_validator.eligibility.validators.rule_based.npi.EligibilityNPIValidator",
    "claim_validator.eligibility.validators.rule_based.payer_id.PayerIDValidator",
    "claim_validator.eligibility.validators.rule_based.service_type.ServiceTypeValidator",
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

    # Prior authorization settings (rule-based only by default — PA is a
    # deterministic lookup, not an interpretation problem)
    pa_rule_validators: list[str] = DEFAULT_PA_RULE_VALIDATORS
    pa_ai_validators: list[str] = []
    pa_skip_ai: bool = True
    pa_skip_ai_on_rule_failure: bool = True

    # Eligibility settings
    eligibility_rule_validators: list[str] = DEFAULT_ELIG_RULE_VALIDATORS
    eligibility_ai_validators: list[str] = DEFAULT_ELIG_AI_VALIDATORS
    eligibility_skip_ai: bool = False
    eligibility_skip_ai_on_rule_failure: bool = True

    # Clearinghouse settings
    clearinghouse_config: dict[str, Any] | None = None

    # Per-stage AI provider overrides for process_claim_full().
    # Each is a dict with keys: provider, api_key, model (+ provider extras).
    # When set, overrides the global ai_config for that specific stage.
    # Example: use Groq for fast summaries, Claude for clinical reasoning.
    ai_claim_analysis_config: dict[str, Any] | None = None
    ai_rejection_summary_config: dict[str, Any] | None = None
    ai_pre_submission_config: dict[str, Any] | None = None
