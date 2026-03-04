"""Eligibility NPI validator — validates provider NPI on eligibility requests.

Thin wrapper around ``shared.validators.validate_npi``.
"""

from __future__ import annotations

from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_npi
from claim_validator.validators.base import BaseValidator


class EligibilityNPIValidator(BaseValidator):
    """Validates provider NPI on eligibility requests."""

    name = "EligibilityNPIValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_npi(
            claim.provider_npi, field_name="provider_npi", code_prefix="ELIG_",
        )
        # Filter MISSING — provider_npi is a required field on the model
        findings = [f for f in shared_findings if f.code != "ELIG_MISSING_NPI"]
        return self._make_output(findings)
