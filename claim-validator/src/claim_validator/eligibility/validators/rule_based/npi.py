"""Eligibility NPI validator — validates provider NPI on eligibility requests."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.rule_based._npi_utils import (
    NPI_REGISTRY_URL,
    _check_luhn_npi,
)


class EligibilityNPIValidator(BaseValidator):
    """Validates provider NPI on eligibility requests."""

    name = "EligibilityNPIValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        npi = claim.provider_npi.strip()

        if len(npi) != 10 or not npi.isdigit():
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_NPI_FORMAT",
                    message="Provider NPI must be exactly 10 numeric digits",
                    severity=Severity.ERROR,
                    field_name="provider_npi",
                    suggestion=f"Verify the NPI format at {NPI_REGISTRY_URL}",
                )
            )
        elif not _check_luhn_npi(npi):
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_NPI",
                    message="Provider NPI fails Luhn check-digit validation",
                    severity=Severity.ERROR,
                    field_name="provider_npi",
                    suggestion=f"Verify the NPI at {NPI_REGISTRY_URL}",
                )
            )

        return self._make_output(findings)
