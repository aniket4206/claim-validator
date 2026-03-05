"""Canonical ICD-10 diagnosis code validation — shared pure function for all domains."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.code_tables import lookup_icd10

_ICD10_RE = re.compile(r"^[A-Za-z]\d{2}(\.?\d{1,4})?$")


def validate_diagnosis(
    codes: list[str] | None,
    field_name: str = "diagnosis_codes",
    code_prefix: str = "",
) -> list[Finding]:
    """Validate ICD-10-CM diagnosis codes against format rules and shared code table.

    Args:
        codes: List of ICD-10 code strings to validate.
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

        if not _ICD10_RE.match(code):
            findings.append(Finding(
                code=f"{code_prefix}INVALID_DIAGNOSIS_FORMAT",
                message=f"Diagnosis code in '{field_name}' has invalid ICD-10 format",
                severity=Severity.ERROR,
                field_name=field_name,
                suggestion="ICD-10 format: letter + 2 digits + optional dot + 1-4 digits",
                context={"position": i + 1},
            ))
            continue

        if lookup_icd10(code) is None:
            findings.append(Finding(
                code=f"{code_prefix}INVALID_DIAGNOSIS",
                message=f"ICD-10 diagnosis code in '{field_name}' not found in code tables",
                severity=Severity.ERROR,
                field_name=field_name,
                suggestion="Verify ICD-10-CM code at https://www.icd10data.com",
                context={"position": i + 1},
            ))

    return findings
