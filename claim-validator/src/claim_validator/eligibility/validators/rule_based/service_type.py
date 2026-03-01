"""Service type validator — validates service type code against bundled code table."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.code_tables.service_types import get_service_type
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator


class ServiceTypeValidator(BaseValidator):
    """Validates service type code exists in X12 service type code table."""

    name = "ServiceTypeValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        if get_service_type(claim.service_type_code) is None:
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_SERVICE_TYPE",
                    message="Service type code not found in X12 service type table",
                    severity=Severity.ERROR,
                    field_name="service_type_code",
                    suggestion=(
                        "Use a valid X12 271 service type code"
                        " (e.g., '30' for health benefit plan coverage)"
                    ),
                    context={"submitted_code": claim.service_type_code.strip()},
                )
            )
        return self._make_output(findings)
