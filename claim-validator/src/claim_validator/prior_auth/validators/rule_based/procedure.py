"""PAProcedureValidator — CPT/HCPCS procedure code validation for PA requests."""

from __future__ import annotations

import re

from claim_validator.code_tables import lookup_hcpcs
from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_PROCEDURE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{5}$")


class PAProcedureValidator(BaseValidator):
    """Validates CPT/HCPCS procedure codes on PA requests."""

    name = "PAProcedureValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []

        if not request.service_lines:
            return self._make_output(findings)

        for idx, line in enumerate(request.service_lines, start=1):
            code = line.cpt_code.strip() if line.cpt_code else ""
            if not code:
                continue

            # Format check
            if not _PROCEDURE_CODE_PATTERN.match(code):
                findings.append(
                    self._make_finding(
                        code="PA_INVALID_PROCEDURE_FORMAT",
                        message=(
                            "Procedure code in 'cpt_code' must be "
                            "exactly 5 alphanumeric characters"
                        ),
                        severity=Severity.ERROR,
                        field_name="cpt_code",
                        line_number=idx,
                        suggestion=(
                            "CPT codes are 5 digits (e.g., 99213). "
                            "HCPCS codes are letter + 4 digits (e.g., J0120)"
                        ),
                    )
                )
                continue

            # Code table lookup
            if lookup_hcpcs(code) is None:
                findings.append(
                    self._make_finding(
                        code="PA_INVALID_PROCEDURE",
                        message=(
                            "Procedure code in 'cpt_code' not found "
                            "in bundled CPT/HCPCS table"
                        ),
                        severity=Severity.ERROR,
                        field_name="cpt_code",
                        line_number=idx,
                        suggestion="Verify the CPT/HCPCS code against the current code set",
                    )
                )

        return self._make_output(findings)
