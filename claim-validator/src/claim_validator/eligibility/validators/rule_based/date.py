"""Date validator — validates date of service for eligibility requests.

Thin wrapper around ``shared.validators.validate_date``.
"""

from __future__ import annotations

from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_date
from claim_validator.validators.base import BaseValidator


class EligibilityDateValidator(BaseValidator):
    """Validates date of service for eligibility requests."""

    name = "EligibilityDateValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_date(
            claim.date_of_service,
            field_name="date_of_service",
            code_prefix="ELIG_",
            max_future_days=365,
            max_past_days=730,
        )
        return self._make_output(shared_findings)
