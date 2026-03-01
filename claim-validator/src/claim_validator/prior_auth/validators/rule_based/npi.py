"""PANPIValidator — NPI validation for prior authorization requests."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.rule_based.npi import _check_luhn_npi

_NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"


class PANPIValidator(BaseValidator):
    """Validates requester NPI on prior authorization requests."""

    name = "PANPIValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []
        npi = request.requester_npi

        # Skip if empty/whitespace — CompletenessValidator handles presence
        if not npi or not npi.strip():
            return self._make_output(findings)

        npi = npi.strip()

        # Format check: exactly 10 numeric digits
        if len(npi) != 10 or not npi.isdigit():
            findings.append(
                self._make_finding(
                    code="PA_INVALID_NPI_FORMAT",
                    message="NPI in 'requester_npi' must be exactly 10 numeric digits",
                    severity=Severity.ERROR,
                    field_name="requester_npi",
                    suggestion=f"Verify the NPI format at {_NPI_REGISTRY_URL}",
                )
            )
            return self._make_output(findings)

        # Luhn check
        if not _check_luhn_npi(npi):
            findings.append(
                self._make_finding(
                    code="PA_INVALID_NPI",
                    message="NPI in 'requester_npi' fails Luhn check-digit validation",
                    severity=Severity.ERROR,
                    field_name="requester_npi",
                    suggestion=f"Verify the NPI at {_NPI_REGISTRY_URL}",
                )
            )

        return self._make_output(findings)
