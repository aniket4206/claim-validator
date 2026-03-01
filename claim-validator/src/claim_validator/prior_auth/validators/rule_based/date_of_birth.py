"""PADateOfBirthValidator — DOB validation for PA requests."""

from __future__ import annotations

from datetime import date

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class PADateOfBirthValidator(BaseValidator):
    """Validates subscriber and patient DOB on PA requests."""

    name = "PADateOfBirthValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []
        today = date.today()

        # Check subscriber DOB
        if request.subscriber.dob > today:
            findings.append(
                self._make_finding(
                    code="PA_INVALID_DOB",
                    message="Date of birth in 'subscriber.dob' must not be in the future",
                    severity=Severity.ERROR,
                    field_name="subscriber.dob",
                    suggestion="Verify the subscriber's date of birth",
                )
            )

        # Check patient DOB if patient is present
        if request.patient is not None and request.patient.dob > today:
            findings.append(
                self._make_finding(
                    code="PA_INVALID_DOB",
                    message="Date of birth in 'patient.dob' must not be in the future",
                    severity=Severity.ERROR,
                    field_name="patient.dob",
                    suggestion="Verify the patient's date of birth",
                )
            )

        return self._make_output(findings)
