"""Date validator — validates date of service for eligibility requests."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

_MAX_FUTURE_DAYS = 365  # 1 year
_MAX_PAST_DAYS = 730    # 2 years


class EligibilityDateValidator(BaseValidator):
    """Validates date of service for eligibility requests."""

    name = "EligibilityDateValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []

        if claim.date_of_service is None:
            findings.append(
                self._make_finding(
                    code="ELIG_MISSING_DATE",
                    message="Date of service is required for eligibility verification",
                    severity=Severity.ERROR,
                    field_name="date_of_service",
                    suggestion="Provide the date of service for the eligibility check",
                )
            )
            return self._make_output(findings)

        today = datetime.date.today()
        delta = (claim.date_of_service - today).days

        if delta > _MAX_FUTURE_DAYS:
            findings.append(
                self._make_finding(
                    code="ELIG_FUTURE_DATE",
                    message="Date of service is more than 1 year in the future",
                    severity=Severity.WARNING,
                    field_name="date_of_service",
                    suggestion="Verify the date of service is correct",
                    context={"delta_days": delta},
                )
            )

        if delta < -_MAX_PAST_DAYS:
            findings.append(
                self._make_finding(
                    code="ELIG_PAST_DATE",
                    message="Date of service is more than 2 years in the past",
                    severity=Severity.WARNING,
                    field_name="date_of_service",
                    suggestion="Verify the date of service is correct",
                    context={"delta_days": delta},
                )
            )

        return self._make_output(findings)
