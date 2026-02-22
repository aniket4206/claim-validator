"""MonetaryValidator -- charge amount and total validation."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_CHARGE_TOLERANCE = 0.01


class MonetaryValidator(BaseValidator):
    """Validates charge amounts and total charge consistency."""

    name = "MonetaryValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_line_charges(claim, findings)
        self._check_total_charge(claim, findings)

        return self._make_output(findings)

    def _check_line_charges(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        for idx, line in enumerate(claim.lines, start=1):
            if line.charge_amount <= 0:
                findings.append(
                    self._make_finding(
                        code="INVALID_CHARGE_AMOUNT",
                        message=(
                            "Charge amount in 'charge_amount'"
                            " must be a positive value"
                        ),
                        severity=Severity.ERROR,
                        field_name="charge_amount",
                        line_number=idx,
                        suggestion=(
                            "Verify the charge amount for"
                            " this service line"
                            " (CMS-1500 Box 24.F)"
                        ),
                    )
                )

    def _check_total_charge(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if claim.total_charge is None or not claim.lines:
            return

        computed_total = sum(
            line.charge_amount * line.units
            for line in claim.lines
        )

        if abs(claim.total_charge - computed_total) > _CHARGE_TOLERANCE:
            findings.append(
                self._make_finding(
                    code="CHARGE_TOTAL_MISMATCH",
                    message=(
                        "Total in 'total_charge' does not"
                        " match sum of line charges"
                    ),
                    severity=Severity.ERROR,
                    field_name="total_charge",
                    suggestion=(
                        "Ensure total charge equals"
                        " the sum of all line"
                        " (charge_amount * units)"
                        " (CMS-1500 Box 28)"
                    ),
                )
            )
