"""Revenue code validator for institutional (UB-04) claims."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.code_tables.revenue_codes import get_revenue_codes_table
from claim_validator.validators.base import BaseValidator


class RevenueCodeValidator(BaseValidator):
    """Validates each service line's revenue code against the bundled table."""

    name = "RevenueCodeValidator"

    def validate(self, claim: Any) -> ValidatorOutput:  # type: ignore[override]
        """Validate revenue codes on institutional claim service lines."""
        service_lines = getattr(claim, "service_lines", None)
        if not service_lines:
            return self._make_output([])

        table = get_revenue_codes_table()
        findings: list[Finding] = []

        for idx, line in enumerate(service_lines, 1):
            rev_code = getattr(line, "revenue_code", None)
            if rev_code is None:
                continue
            normalized = str(rev_code).strip().zfill(4)
            if normalized not in table:
                findings.append(self._make_finding(
                    code="INST_INVALID_REVENUE_CODE",
                    message=f"Service line {idx}: unknown revenue code '{rev_code}'",
                    severity=Severity.ERROR,
                    field_name="service_lines",
                    line_number=idx,
                    suggestion="Use a valid 4-digit UB-04 revenue code",
                ))

        return self._make_output(findings)
