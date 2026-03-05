"""NPIValidator — Luhn check-digit validation for NPI numbers.

Thin wrapper around ``shared.validators.validate_npi``.
"""

from __future__ import annotations

from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.validators import validate_npi
from claim_validator.shared.validators.npi import (
    _check_luhn_npi,  # noqa: F401 — re-exported for tests
)
from claim_validator.validators.base import BaseValidator


class NPIValidator(BaseValidator):
    """Validates NPI numbers using the Luhn check-digit algorithm."""

    name = "NPIValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        # Claim-level NPIs
        self._check_npi(claim.billing_provider_npi, "billing_provider_npi", None, findings)
        self._check_npi(
            claim.rendering_provider_npi, "rendering_provider_npi", None, findings
        )

        # Line-level rendering NPI
        for idx, line in enumerate(claim.lines, start=1):
            self._check_npi(
                line.rendering_provider_npi, "rendering_provider_npi", idx, findings
            )

        return self._make_output(findings)

    def _check_npi(
        self,
        value: str | None,
        field_name: str,
        line_number: int | None,
        findings: list[Finding],
    ) -> None:
        """Validate a single NPI value. Skip None/empty (CompletenessValidator handles required)."""
        if not value or not value.strip():
            return

        shared_findings = validate_npi(value, field_name=field_name)
        for f in shared_findings:
            if f.code == "MISSING_NPI":
                continue  # Claims skips missing — handled by CompletenessValidator
            if line_number is not None:
                findings.append(f.model_copy(update={"line_number": line_number}))
            else:
                findings.append(f)
