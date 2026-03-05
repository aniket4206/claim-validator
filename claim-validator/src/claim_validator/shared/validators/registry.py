"""Shared validator registry — maps short string IDs to canonical pure functions.

This registry is separate from the existing ``ValidatorRegistry`` in
``validators/registry.py`` which handles class-based ``BaseValidator``
subclasses via dotted-path loading.  This module provides a parallel
lookup for the shared pure functions created in Epic 1 (Stories 1.1/1.3).
"""

from __future__ import annotations

from collections.abc import Callable

from claim_validator.exceptions import ConfigurationError
from claim_validator.models.results import Finding

# Type alias — shared validators have varying signatures (single-value,
# multi-value, demographics) so we use ``Callable[..., list[Finding]]``.
ValidatorFunc = Callable[..., list[Finding]]

VALIDATORS: dict[str, ValidatorFunc] = {}


def _register_all() -> None:
    """Populate the registry with all shared validators at module load time."""
    from claim_validator.shared.validators.date import validate_date
    from claim_validator.shared.validators.demographics import validate_demographics
    from claim_validator.shared.validators.diagnosis import validate_diagnosis
    from claim_validator.shared.validators.member_id import validate_member_id
    from claim_validator.shared.validators.npi import validate_npi
    from claim_validator.shared.validators.payer_id import validate_payer_id
    from claim_validator.shared.validators.procedure import validate_procedure

    VALIDATORS.update(
        {
            "npi": validate_npi,
            "date": validate_date,
            "member_id": validate_member_id,
            "demographics": validate_demographics,
            "diagnosis": validate_diagnosis,
            "procedure": validate_procedure,
            "payer_id": validate_payer_id,
        }
    )


_register_all()


def get_validator(name: str) -> ValidatorFunc:
    """Look up a shared validator by its short string ID.

    Args:
        name: Validator identifier (e.g. ``"npi"``, ``"diagnosis"``).

    Returns:
        The corresponding validator function.

    Raises:
        ConfigurationError: If *name* is not a registered validator ID.
    """
    try:
        return VALIDATORS[name]
    except KeyError:
        raise ConfigurationError(
            f"Unknown shared validator '{name}'. "
            f"Available: {', '.join(sorted(VALIDATORS))}"
        ) from None


def list_validators() -> list[str]:
    """Return all registered validator IDs in sorted order."""
    return sorted(VALIDATORS.keys())
