"""Bill type validator for institutional (UB-04) claims."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# Valid UB-04 bill type positions
# Position 1: Type of facility (1-8)
_VALID_FACILITY_TYPES = {"1", "2", "3", "4", "5", "6", "7", "8"}
# Position 2: Bill classification (1-9)
_VALID_CLASSIFICATIONS = {"1", "2", "3", "4", "5", "6", "7", "8", "9"}
# Position 3: Frequency (0-9, A-G, J-P, Z)
_VALID_FREQUENCIES = set("0123456789ABCDEFGJKLMNOPZ")


class BillTypeValidator(BaseValidator):
    """Validates the 3-digit UB-04 bill type code structure.

    Position 1: facility type, Position 2: classification,
    Position 3: frequency code.
    """

    name = "BillTypeValidator"

    def validate(self, claim: Any) -> ValidatorOutput:  # type: ignore[override]
        """Validate bill_type_code on an institutional claim."""
        bill_type = getattr(claim, "bill_type_code", None)
        if bill_type is None:
            return self._make_output([])

        findings: list[Finding] = []
        code = str(bill_type).strip()

        if len(code) != 3:
            findings.append(self._make_finding(
                code="INST_INVALID_BILL_TYPE",
                message=f"Bill type code must be exactly 3 digits, got {len(code)}",
                severity=Severity.ERROR,
                field_name="bill_type_code",
                suggestion="Use a valid 3-digit UB-04 bill type code (e.g. '111', '131')",
            ))
            return self._make_output(findings)

        if code[0] not in _VALID_FACILITY_TYPES:
            findings.append(self._make_finding(
                code="INST_INVALID_BILL_TYPE",
                message=f"Bill type position 1 (facility type) '{code[0]}' is invalid",
                severity=Severity.ERROR,
                field_name="bill_type_code",
                suggestion="Position 1 must be 1-8",
            ))

        if code[1] not in _VALID_CLASSIFICATIONS:
            findings.append(self._make_finding(
                code="INST_INVALID_BILL_TYPE",
                message=f"Bill type position 2 (classification) '{code[1]}' is invalid",
                severity=Severity.ERROR,
                field_name="bill_type_code",
                suggestion="Position 2 must be 1-9",
            ))

        if code[2].upper() not in _VALID_FREQUENCIES:
            findings.append(self._make_finding(
                code="INST_INVALID_BILL_TYPE",
                message=f"Bill type position 3 (frequency) '{code[2]}' is invalid",
                severity=Severity.ERROR,
                field_name="bill_type_code",
                suggestion="Position 3 must be 0-9 or A-G, J-P, Z",
            ))

        return self._make_output(findings)
