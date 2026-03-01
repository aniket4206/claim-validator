"""NPIValidator — Luhn check-digit validation for NPI numbers."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.rule_based._npi_utils import (
    NPI_REGISTRY_URL,
    _check_luhn_npi,
)


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
        """Validate a single NPI value. Skip None/empty."""
        if not value or not value.strip():
            return

        npi = value.strip()

        # Format check: exactly 10 numeric digits
        if len(npi) != 10 or not npi.isdigit():
            findings.append(
                self._make_finding(
                    code="INVALID_NPI_FORMAT",
                    message=f"NPI in '{field_name}' must be exactly 10 numeric digits",
                    severity=Severity.ERROR,
                    field_name=field_name,
                    line_number=line_number,
                    suggestion=f"Verify the NPI format at {NPI_REGISTRY_URL}",
                )
            )
            return  # Skip Luhn check if format is wrong

        # Luhn check
        if not _check_luhn_npi(npi):
            findings.append(
                self._make_finding(
                    code="INVALID_NPI",
                    message=f"NPI in '{field_name}' fails Luhn check-digit validation",
                    severity=Severity.ERROR,
                    field_name=field_name,
                    line_number=line_number,
                    suggestion=f"Verify the NPI at {NPI_REGISTRY_URL}",
                )
            )
