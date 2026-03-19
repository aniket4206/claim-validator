"""Institutional completeness validator for UB-04 claims."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class InstitutionalCompletenessValidator(BaseValidator):
    """Checks all UB-04 required fields are present."""

    name = "InstitutionalCompletenessValidator"

    def validate(self, claim: Any) -> ValidatorOutput:  # type: ignore[override]
        """Validate required UB-04 fields are present."""
        findings: list[Finding] = []

        # Required: attending physician NPI
        if not getattr(claim, "attending_physician_npi", None):
            findings.append(self._make_finding(
                code="INST_MISSING_ATTENDING_NPI",
                message="Attending physician NPI is required for institutional claims",
                severity=Severity.ERROR,
                field_name="attending_physician_npi",
            ))

        # Required: bill type code
        if not getattr(claim, "bill_type_code", None):
            findings.append(self._make_finding(
                code="INST_MISSING_BILL_TYPE",
                message="Bill type code is required for institutional claims",
                severity=Severity.ERROR,
                field_name="bill_type_code",
            ))

        # Required: at least one service line with revenue code
        service_lines = getattr(claim, "service_lines", [])
        if not service_lines:
            findings.append(self._make_finding(
                code="INST_MISSING_SERVICE_LINES",
                message="At least one service line with a revenue code is required",
                severity=Severity.ERROR,
                field_name="service_lines",
            ))
        else:
            has_revenue = any(
                getattr(line, "revenue_code", None) for line in service_lines
            )
            if not has_revenue:
                findings.append(self._make_finding(
                    code="INST_MISSING_REVENUE_CODE",
                    message="At least one service line must have a revenue code",
                    severity=Severity.ERROR,
                    field_name="service_lines",
                ))

        # Required: billing provider NPI
        if not getattr(claim, "billing_provider_npi", None):
            findings.append(self._make_finding(
                code="INST_MISSING_BILLING_NPI",
                message="Billing provider NPI is required",
                severity=Severity.ERROR,
                field_name="billing_provider_npi",
            ))

        # Required: subscriber ID
        if not getattr(claim, "subscriber_id", None):
            findings.append(self._make_finding(
                code="INST_MISSING_SUBSCRIBER_ID",
                message="Subscriber ID is required",
                severity=Severity.ERROR,
                field_name="subscriber_id",
            ))

        return self._make_output(findings)
