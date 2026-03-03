"""Stage-based validator configuration — maps pipeline stages to shared validator lists.

Each domain (claims, eligibility, prior-auth) can define which shared
validators to run in a given pipeline stage via ``StageValidatorConfig``.
Default configurations mirror the shared validators currently used by each
domain's existing class-based pipeline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from claim_validator.exceptions import ConfigurationError
from claim_validator.models.results import Finding
from claim_validator.shared.validators.registry import (
    ValidatorFunc,
    get_validator,
)

# ---------------------------------------------------------------------------
# Stage configuration model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageValidatorConfig:
    """Immutable configuration mapping a pipeline stage to shared validator IDs.

    Attributes:
        validators: Ordered tuple of validator IDs to run in this stage.
    """

    validators: tuple[str, ...]

    def resolve(self) -> tuple[ValidatorFunc, ...]:
        """Resolve validator IDs to their functions.

        Returns:
            Tuple of validator functions in the same order as *validators*.

        Raises:
            ConfigurationError: If any validator ID is not registered.
        """
        return tuple(get_validator(v) for v in self.validators)


# ---------------------------------------------------------------------------
# Domain defaults — shared validators only (domain-specific validators like
# Completeness, Monetary, Duplicate etc. remain in BaseValidator system)
# ---------------------------------------------------------------------------

DEFAULT_CLAIM_VALIDATORS: tuple[str, ...] = (
    "npi",
    "member_id",
    "demographics",
    "diagnosis",
    "procedure",
)
DEFAULT_ELIGIBILITY_VALIDATORS: tuple[str, ...] = (
    "date",
    "demographics",
    "member_id",
    "npi",
    "payer_id",
)
DEFAULT_PA_VALIDATORS: tuple[str, ...] = (
    "date",
    "diagnosis",
    "member_id",
    "npi",
    "procedure",
)

_DOMAIN_DEFAULTS: dict[str, tuple[str, ...]] = {
    "claim": DEFAULT_CLAIM_VALIDATORS,
    "eligibility": DEFAULT_ELIGIBILITY_VALIDATORS,
    "prior_auth": DEFAULT_PA_VALIDATORS,
}


def get_default_stage_config(domain: str) -> StageValidatorConfig:
    """Return the default shared-validator stage config for *domain*.

    Args:
        domain: One of ``"claim"``, ``"eligibility"``, or ``"prior_auth"``.

    Returns:
        A ``StageValidatorConfig`` pre-loaded with the validators that
        each domain's existing pipeline currently uses.

    Raises:
        ConfigurationError: If *domain* is not recognised.
    """
    if domain not in _DOMAIN_DEFAULTS:
        raise ConfigurationError(
            f"Unknown domain '{domain}'. "
            f"Available: {', '.join(sorted(_DOMAIN_DEFAULTS))}"
        )
    return StageValidatorConfig(validators=_DOMAIN_DEFAULTS[domain])


# ---------------------------------------------------------------------------
# Stage runner
# ---------------------------------------------------------------------------


def run_stage_validators(
    config: StageValidatorConfig,
    data_extractor: Callable[[str], dict[str, Any]],
    code_prefix: str = "",
) -> list[Finding]:
    """Run all validators in a stage config with domain-specific parameters.

    Args:
        config: Stage configuration with validator IDs.
        data_extractor: Callable that takes a validator ID and returns
            a ``dict`` of keyword arguments for that validator function.
            Must include the value argument(s) at minimum.
            ``code_prefix`` is injected automatically when not provided
            by *data_extractor*.
        code_prefix: Domain prefix for finding codes (e.g. ``"PA_"``).

    Returns:
        Aggregated list of findings from all validators.
    """
    findings: list[Finding] = []
    validators = config.resolve()
    for vid, func in zip(config.validators, validators):
        kwargs = {**data_extractor(vid)}
        if "code_prefix" not in kwargs:
            kwargs["code_prefix"] = code_prefix
        findings.extend(func(**kwargs))
    return findings
