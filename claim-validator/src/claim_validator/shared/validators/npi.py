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


def _compute_correct_npi(npi: str) -> str | None:
    """Compute the correct check digit for a 10-digit NPI.

    Takes the first 9 digits, calculates the proper Luhn check digit
    using the '80840' healthcare prefix, and returns the corrected NPI.
    """
    try:
        base9 = npi[:9]
        if len(base9) != 9 or not base9.isdigit():
            return None

        # Prefix + 9 base digits + placeholder check digit (0)
        prefixed = "80840" + base9 + "0"
        total = 0
        for i, ch in enumerate(reversed(prefixed)):
            digit = int(ch)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit

        # Check digit is what makes total a multiple of 10
        check_digit = (10 - (total % 10)) % 10
        return base9 + str(check_digit)
    except (ValueError, TypeError):
        return None


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

    # Luhn check — WARNING (not error) so user can still proceed
    if not _check_luhn_npi(cleaned):
        corrected = _compute_correct_npi(cleaned)
        suggestion = (
            f"NPI check digit appears incorrect. "
            f"Did you mean {corrected}? "
            f"Verify at {_NPI_REGISTRY_URL}"
        ) if corrected else f"Verify the NPI at {_NPI_REGISTRY_URL}"

        findings.append(Finding(
            code=f"{code_prefix}INVALID_NPI",
            message=f"NPI '{cleaned}' fails Luhn check-digit validation",
            severity=Severity.WARNING,
            field_name=field_name,
            suggestion=suggestion,
            context={"check": "luhn", "suggested_npi": corrected},
        ))

    return findings
