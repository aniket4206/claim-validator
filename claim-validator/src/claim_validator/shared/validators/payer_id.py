"""Canonical payer ID validation — shared pure function for all domains."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.code_tables import lookup_payer


def validate_payer_id(
    payer_id: str | None,
    field_name: str = "payer_id",
    code_prefix: str = "",
) -> list[Finding]:
    """Validate a payer identifier against the shared payer directory.

    Args:
        payer_id: The payer ID string to validate.
        field_name: Name of the field being validated (for Finding output).
        code_prefix: Prefix for finding codes (e.g. ``"ELIG_"`` or ``"PA_"``).

    Returns:
        List of findings. Empty list means payer ID is valid.
    """
    if not payer_id or not payer_id.strip():
        return [Finding(
            code=f"{code_prefix}MISSING_PAYER_ID",
            message=f"Payer ID is required in '{field_name}'",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Provide a valid payer identifier",
        )]

    cleaned = payer_id.strip()

    if lookup_payer(cleaned) is None:
        return [Finding(
            code=f"{code_prefix}INVALID_PAYER",
            message=f"Payer ID in '{field_name}' not found in payer directory",
            severity=Severity.WARNING,
            field_name=field_name,
            suggestion="Verify payer ID against the current payer directory",
        )]

    return []
