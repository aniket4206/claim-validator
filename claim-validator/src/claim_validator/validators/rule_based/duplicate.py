"""DuplicateValidator -- duplicate claim line detection."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class DuplicateValidator(BaseValidator):
    """Detects duplicate claim lines within a single claim."""

    name = "DuplicateValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_duplicate_lines(claim, findings)

        return self._make_output(findings)

    def _check_duplicate_lines(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        seen: dict[tuple[str, tuple[str, ...], str], int] = {}

        for idx, line in enumerate(claim.lines, start=1):
            key = (
                line.procedure_code.strip(),
                tuple(sorted(line.modifiers)),
                (line.service_date_from or "").strip(),
            )

            if key in seen:
                findings.append(
                    self._make_finding(
                        code="DUPLICATE_LINE",
                        message=(
                            "Service line in 'lines'"
                            " appears to be a duplicate"
                            " of an earlier line"
                        ),
                        severity=Severity.WARNING,
                        field_name="lines",
                        line_number=idx,
                        suggestion=(
                            "Review duplicate service"
                            " lines — if intentional,"
                            " add distinguishing"
                            " modifiers (e.g., 50, LT,"
                            " RT)"
                        ),
                    )
                )
            else:
                seen[key] = idx
