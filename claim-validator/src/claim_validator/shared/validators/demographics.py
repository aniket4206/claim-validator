"""Canonical demographics validation — shared pure function for all domains."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.models.results import Finding

_VALID_GENDERS = {"M", "F", "U"}


def validate_demographics(
    name: str | None,
    gender: str | None,
    dob: str | None,
    field_prefix: str = "",
    code_prefix: str = "",
) -> list[Finding]:
    """Validate patient demographics: name, gender, and date of birth.

    Args:
        name: Patient name (first or full). None or empty triggers a finding.
        gender: Patient gender code (``M``, ``F``, or ``U``).
        dob: Patient date of birth as ISO string (``YYYY-MM-DD``).
        field_prefix: Prefix for field names (e.g. ``"patient_"`` or ``"subscriber_"``).
        code_prefix: Prefix for finding codes (e.g. ``"ELIG_"`` or ``"PA_"``).

    Returns:
        List of findings. Empty list means all demographics are valid.
    """
    findings: list[Finding] = []

    _check_name(name, field_prefix, code_prefix, findings)
    _check_gender(gender, field_prefix, code_prefix, findings)
    _check_dob(dob, field_prefix, code_prefix, findings)

    return findings


def _check_name(
    name: str | None,
    field_prefix: str,
    code_prefix: str,
    findings: list[Finding],
) -> None:
    """Check that patient name is present."""
    if not name or not name.strip():
        findings.append(Finding(
            code=f"{code_prefix}MISSING_PATIENT_NAME",
            message=f"Patient name is required in '{field_prefix}name'",
            severity=Severity.ERROR,
            field_name=f"{field_prefix}name",
            suggestion="Provide the patient's name",
        ))


def _check_gender(
    gender: str | None,
    field_prefix: str,
    code_prefix: str,
    findings: list[Finding],
) -> None:
    """Check that gender is a valid code (M, F, or U)."""
    if not gender or not gender.strip():
        return  # Gender not always required; presence checks are domain-specific

    if gender.strip().upper() not in _VALID_GENDERS:
        findings.append(Finding(
            code=f"{code_prefix}INVALID_GENDER",
            message=f"Field '{field_prefix}gender' must be one of: M, F, U",
            severity=Severity.ERROR,
            field_name=f"{field_prefix}gender",
            suggestion="Use M (male), F (female), or U (unknown) for patient gender",
        ))


def _check_dob(
    dob: str | None,
    field_prefix: str,
    code_prefix: str,
    findings: list[Finding],
) -> None:
    """Check that DOB is a valid date not in the future.

    NOTE: This intentionally does NOT delegate to ``validate_date()`` because
    DOB semantics differ from generic dates:
    - Missing DOB is not an error here (domain decides if required)
    - Future DOB is an ERROR, not a WARNING
    - There is no "too far in the past" check for DOB
    - Finding codes use ``FUTURE_DOB`` / ``INVALID_DOB_FORMAT``, not ``FUTURE_DATE``
    """
    if not dob or not dob.strip():
        return  # DOB presence checks are domain-specific

    try:
        dob_date = datetime.date.fromisoformat(dob.strip())
    except ValueError:
        findings.append(Finding(
            code=f"{code_prefix}INVALID_DOB_FORMAT",
            message=f"Field '{field_prefix}dob' must be a valid date in YYYY-MM-DD format",
            severity=Severity.ERROR,
            field_name=f"{field_prefix}dob",
            suggestion="Provide date of birth in YYYY-MM-DD format",
        ))
        return

    if dob_date > datetime.date.today():
        findings.append(Finding(
            code=f"{code_prefix}FUTURE_DOB",
            message=f"Field '{field_prefix}dob' is in the future",
            severity=Severity.ERROR,
            field_name=f"{field_prefix}dob",
            suggestion="Verify the patient date of birth",
        ))
