"""Canonical date validation — shared pure function for all domains."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.models.results import Finding

_MAX_FUTURE_DAYS = 365  # 1 year
_MAX_PAST_DAYS = 730  # 2 years


def validate_date(
    value: str | datetime.date | None,
    field_name: str = "date",
    code_prefix: str = "",
    *,
    max_future_days: int = _MAX_FUTURE_DAYS,
    max_past_days: int = _MAX_PAST_DAYS,
) -> list[Finding]:
    """Validate a date value for presence, format, and reasonable range.

    Args:
        value: Date as ISO string (``YYYY-MM-DD``), ``datetime.date``, or None.
            ``datetime.datetime`` objects are accepted and coerced to date.
        field_name: Name of the field being validated (for Finding output).
        code_prefix: Prefix for finding codes (e.g. ``"ELIG_"`` or ``"PA_"``).
        max_future_days: Days into the future before a WARNING is raised.
        max_past_days: Days into the past before a WARNING is raised.

    Returns:
        List of findings. Empty list means the date is valid.
    """
    findings: list[Finding] = []

    # Fix #2 + #4: Consolidated missing check; datetime.datetime guard
    if value is None or (isinstance(value, str) and not value.strip()):
        findings.append(Finding(
            code=f"{code_prefix}MISSING_DATE",
            message=f"Date is required in '{field_name}'",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Provide a valid date in YYYY-MM-DD format",
        ))
        return findings

    # Parse string to date, or coerce datetime.datetime → date
    if isinstance(value, str):
        try:
            parsed = datetime.date.fromisoformat(value.strip())
        except ValueError:
            findings.append(Finding(
                code=f"{code_prefix}INVALID_DATE_FORMAT",
                message=f"Field '{field_name}' must be a valid date in YYYY-MM-DD format",
                severity=Severity.ERROR,
                field_name=field_name,
                suggestion="Provide the date in YYYY-MM-DD format",
            ))
            return findings
    elif isinstance(value, datetime.datetime):
        parsed = value.date()
    else:
        parsed = value

    # Range checks
    today = datetime.date.today()
    delta = (parsed - today).days

    if delta > max_future_days:
        findings.append(Finding(
            code=f"{code_prefix}FUTURE_DATE",
            message=f"Date in '{field_name}' is more than {max_future_days} days in the future",
            severity=Severity.WARNING,
            field_name=field_name,
            suggestion="Verify the date is correct",
            context={"delta_days": delta},
        ))

    if delta < -max_past_days:
        findings.append(Finding(
            code=f"{code_prefix}PAST_DATE",
            message=f"Date in '{field_name}' is more than {max_past_days} days in the past",
            severity=Severity.WARNING,
            field_name=field_name,
            suggestion="Verify the date is correct",
            context={"delta_days": delta},
        ))

    return findings
