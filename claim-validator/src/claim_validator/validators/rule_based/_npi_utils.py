"""Shared NPI validation utilities — used by claim and eligibility validators."""

from __future__ import annotations

NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"


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
        prefixed = "80840" + base9 + "0"
        total = 0
        for i, ch in enumerate(reversed(prefixed)):
            digit = int(ch)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        check_digit = (10 - (total % 10)) % 10
        return base9 + str(check_digit)
    except (ValueError, TypeError):
        return None
