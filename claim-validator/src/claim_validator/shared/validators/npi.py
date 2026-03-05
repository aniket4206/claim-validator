"""Canonical NPI validation — shared pure function for all domains."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding

_NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"


def _check_luhn_npi(npi: str) -> bool:
    """Validate NPI using Luhn algorithm with '80840' healthcare prefix."""
    try:
        prefixed = "80840" + npi
        total = 0
        for i, ch in enumerate(reversed(prefixed)):
            digit = int(ch)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0
    except (ValueError, TypeError):
        return False


def validate_npi(
    npi: str | None,
    field_name: str = "npi",
    code_prefix: str = "",
) -> list[Finding]:
    """Validate an NPI number using format and Luhn check-digit rules.

    Args:
        npi: The NPI string to validate (10 numeric digits).
        field_name: Name of the field being validated (for Finding output).
        code_prefix: Prefix for finding codes (e.g. ``"ELIG_"`` or ``"PA_"``).

    Returns:
        List of findings. Empty list means NPI is valid.
    """
    findings: list[Finding] = []

    if not npi or not npi.strip():
        findings.append(Finding(
            code=f"{code_prefix}MISSING_NPI",
            message=f"NPI is required in '{field_name}'",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Provide a valid 10-digit NPI",
        ))
        return findings

    cleaned = npi.strip()

    # Format check: exactly 10 numeric digits
    if len(cleaned) != 10 or not cleaned.isdigit():
        findings.append(Finding(
            code=f"{code_prefix}INVALID_NPI_FORMAT",
            message=f"NPI in '{field_name}' must be exactly 10 numeric digits",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion=f"Verify the NPI format at {_NPI_REGISTRY_URL}",
            context={"npi_length": len(cleaned)},
        ))
        return findings

    # Luhn check
    if not _check_luhn_npi(cleaned):
        findings.append(Finding(
            code=f"{code_prefix}INVALID_NPI",
            message=f"NPI in '{field_name}' fails Luhn check-digit validation",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion=f"Verify the NPI at {_NPI_REGISTRY_URL}",
            context={"check": "luhn"},
        ))

    return findings
