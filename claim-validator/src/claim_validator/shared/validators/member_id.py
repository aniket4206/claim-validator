"""Canonical member/subscriber ID validation — shared pure function for all domains."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.results import Finding

_ALPHANUMERIC_PATTERN = re.compile(r"[A-Za-z0-9]")
_DEFAULT_MIN_ALPHANUMERIC = 2


def validate_member_id(
    member_id: str | None,
    field_name: str = "member_id",
    code_prefix: str = "",
    *,
    min_alphanumeric: int = _DEFAULT_MIN_ALPHANUMERIC,
) -> list[Finding]:
    """Validate a member/subscriber ID for presence and format.

    Args:
        member_id: The member or subscriber ID string.
        field_name: Name of the field being validated (for Finding output).
        code_prefix: Prefix for finding codes (e.g. ``"ELIG_"`` or ``"PA_"``).
        min_alphanumeric: Minimum number of alphanumeric characters required.

    Returns:
        List of findings. Empty list means the member ID is valid.
    """
    findings: list[Finding] = []

    if not member_id or not member_id.strip():
        findings.append(Finding(
            code=f"{code_prefix}MISSING_MEMBER_ID",
            message=f"Member ID is required in '{field_name}'",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Provide the subscriber/member ID from the insurance card",
        ))
        return findings

    cleaned = member_id.strip()
    alphanumeric_count = len(_ALPHANUMERIC_PATTERN.findall(cleaned))

    if alphanumeric_count < min_alphanumeric:
        findings.append(Finding(
            code=f"{code_prefix}INVALID_MEMBER_ID",
            message=(
                f"Member ID in '{field_name}' must contain at least "
                f"{min_alphanumeric} alphanumeric characters"
            ),
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Verify the member/subscriber ID from the insurance card",
            context={
                "alphanumeric_count": alphanumeric_count,
                "id_length": len(cleaned),
            },
        ))

    return findings
