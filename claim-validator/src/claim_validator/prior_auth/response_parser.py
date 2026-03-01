"""278 response parser — parse raw 278 JSON into PriorAuthResponse model."""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.prior_auth.code_tables.aaa_reject_codes import (
    get_aaa_reject_code,
)
from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.models.response import (
    PriorAuthError,
    PriorAuthResponse,
    ServiceLineDecision,
)

ParsedResponse = tuple[PriorAuthResponse, list[Finding]]


def parse_278_response(raw: dict[str, Any]) -> ParsedResponse:
    """Parse a raw 278 JSON dict into a structured PriorAuthResponse.

    Pure function — no network calls, no side effects, no mutation of raw dict.

    Args:
        raw: Raw 278 JSON dict from a clearinghouse.

    Returns:
        Tuple of (PriorAuthResponse, list[Finding]) where findings contain
        any issues encountered during parsing (ERROR for known AAA reject
        codes, WARNING for unmapped codes or action codes).
    """
    findings: list[Finding] = []

    # Preserve original dict unmodified
    raw_copy: dict[str, Any] = copy.deepcopy(raw)

    # Extract top-level action code (support both key conventions)
    raw_action = raw.get("action_code")
    if raw_action is None:
        raw_action = raw.get("hcr01")
    action_code = _parse_action_code(raw_action, findings)

    # Extract authorization number
    authorization_number = raw.get("authorization_number")
    if authorization_number is not None:
        authorization_number = str(authorization_number)

    # Extract dates
    effective_date = _parse_date(raw.get("effective_date"))
    expiration_date = _parse_date(raw.get("expiration_date"))

    # Extract decision reason (for denied/modified responses)
    decision_reason_code = raw.get("decision_reason_code")
    if decision_reason_code is not None:
        decision_reason_code = str(decision_reason_code)

    decision_reason_description = raw.get("decision_reason_description")
    if decision_reason_description is not None:
        decision_reason_description = str(decision_reason_description)

    # Parse service line decisions
    service_line_decisions = _parse_service_lines(
        raw.get("service_lines", []),
        findings,
    )

    # Parse AAA error segments
    raw_aaa = raw.get("aaa_errors")
    if raw_aaa is None:
        raw_aaa = raw.get("aaa_segments")
    aaa_errors = _parse_aaa_errors(raw_aaa, findings)

    response = PriorAuthResponse(
        action_code=action_code,
        authorization_number=authorization_number,
        effective_date=effective_date,
        expiration_date=expiration_date,
        decision_reason_code=decision_reason_code,
        decision_reason_description=decision_reason_description,
        service_line_decisions=service_line_decisions,
        errors=aaa_errors,
        raw_response=raw_copy,
    )

    return response, findings


def _parse_action_code(
    raw_code: Any,
    findings: list[Finding],
) -> CertificationActionCode | None:
    """Map a raw action code string to CertificationActionCode enum.

    Returns None and appends a WARNING finding for unmapped codes.
    """
    if raw_code is None:
        return None

    code_str = str(raw_code).upper().strip()
    if not code_str:
        return None

    try:
        return CertificationActionCode(code_str)
    except ValueError:
        findings.append(
            Finding(
                code="PA_UNKNOWN_ACTION_CODE",
                message="Unknown HCR action code encountered in 278 response",
                severity=Severity.WARNING,
                field_name="action_code",
                suggestion="Check 278 response for updated action code values",
                context={"raw_code": code_str},
            )
        )
        return None


def _parse_date(value: Any) -> date | None:
    """Parse a date value from raw 278 JSON. Returns None on failure."""
    if value is None:
        return None

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _parse_aaa_errors(
    raw_errors: Any,
    findings: list[Finding],
) -> list[PriorAuthError]:
    """Parse raw AAA error dicts into PriorAuthError models.

    For each AAA error, maps the rejection code to a human-readable message
    via the bundled code table and appends an AAA_PA_REJECTION Finding.

    Unknown codes get a generic message and a WARNING finding (NFR18).
    """
    if not isinstance(raw_errors, list):
        return []

    errors: list[PriorAuthError] = []
    for item in raw_errors:
        if not isinstance(item, dict):
            continue

        # Extract rejection code (support both key conventions)
        rejection_code = item.get("rejection_code")
        if rejection_code is None:
            rejection_code = item.get("aaa03")
        if rejection_code is None:
            continue
        rejection_code = str(rejection_code).upper().strip()
        if not rejection_code:
            continue

        # Extract follow-up code (support both key conventions)
        follow_up_code = item.get("follow_up_code")
        if follow_up_code is None:
            follow_up_code = item.get("aaa04")
        if follow_up_code is not None:
            follow_up_code = str(follow_up_code).upper().strip() or None

        # Look up human-readable message from code table
        code_info = get_aaa_reject_code(rejection_code)

        if code_info is not None:
            message = code_info["description"]
            suggested_fix = code_info["suggested_fix"]
            meaning = code_info["meaning"]
            severity = Severity.ERROR
        else:
            message = "Unknown AAA reject code"
            suggested_fix = "Contact payer for details"
            meaning = "Unknown"
            severity = Severity.WARNING

        error = PriorAuthError(
            rejection_code=rejection_code,
            follow_up_code=follow_up_code,
            message=message,
            suggested_fix=suggested_fix,
        )
        errors.append(error)

        findings.append(
            Finding(
                code="AAA_PA_REJECTION",
                message=message,
                severity=severity,
                field_name="aaa_segment",
                suggestion=suggested_fix,
                context={
                    "rejection_code": rejection_code,
                    "follow_up_code": follow_up_code,
                    "meaning": meaning,
                },
            )
        )

    return errors


def _parse_service_lines(
    raw_lines: Any,
    findings: list[Finding],
) -> list[ServiceLineDecision]:
    """Parse raw service line dicts into ServiceLineDecision models."""
    if not isinstance(raw_lines, list):
        return []

    decisions: list[ServiceLineDecision] = []
    for item in raw_lines:
        if not isinstance(item, dict):
            continue

        # Parse per-line action code
        line_raw_code = item.get("action_code")
        line_action = _parse_action_code(line_raw_code, findings)

        # Parse approved quantity
        approved_qty = item.get("approved_quantity")
        if approved_qty is not None:
            try:
                approved_qty = int(approved_qty)
            except (ValueError, TypeError):
                approved_qty = None

        decision = ServiceLineDecision(
            cpt_code=item.get("cpt_code"),
            action_code=line_action,
            authorization_number=item.get("authorization_number"),
            approved_quantity=approved_qty,
            denied_reason=item.get("denied_reason"),
        )
        decisions.append(decision)

    return decisions
