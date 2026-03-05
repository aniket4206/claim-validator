"""Canonical CPT/HCPCS procedure code validation — shared pure function for all domains."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.code_tables import lookup_hcpcs

_HCPCS_RE = re.compile(r"^[A-Za-z0-9]{5}$")


def validate_procedure(
    codes: list[str] | None,
    field_name: str = "procedure_codes",
    code_prefix: str = "",
) -> list[Finding]:
    """Validate CPT/HCPCS procedure codes against format rules and shared code table.

    Args:
        codes: List of CPT/HCPCS code strings to validate.
        field_name: Name of the field being validated (for Finding output).
        code_prefix: Prefix for finding codes (e.g. ``"CLM_"`` or ``"PA_"``).

    Returns:
        List of findings. Empty list means all codes are valid.
    """
    if not codes:
        return []

    findings: list[Finding] = []

    for i, raw_code in enumerate(codes):
        code = raw_code.strip()

        if not _HCPCS_RE.match(code):
            findings.append(Finding(
                code=f"{code_prefix}INVALID_PROCEDURE_FORMAT",
                message=f"Procedure code in '{field_name}' has invalid CPT/HCPCS format",
                severity=Severity.ERROR,
                field_name=field_name,
                suggestion="CPT/HCPCS format: exactly 5 alphanumeric characters",
                context={"position": i + 1},
            ))
            continue

        if lookup_hcpcs(code) is None:
            findings.append(Finding(
                code=f"{code_prefix}INVALID_PROCEDURE",
                message=f"Procedure code in '{field_name}' not found in code tables",
                severity=Severity.WARNING,
                field_name=field_name,
                suggestion="Verify CPT/HCPCS code with current AMA or CMS reference",
                context={"position": i + 1},
            ))

    return findings
