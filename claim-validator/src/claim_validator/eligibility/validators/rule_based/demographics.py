"""Demographics validator — validates subscriber and dependent completeness."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

_REQUIRED_SUBSCRIBER_FIELDS = [
    ("subscriber_first_name", "Provide the subscriber's first name"),
    ("subscriber_last_name", "Provide the subscriber's last name"),
    # subscriber_dob is a required `date` field — Pydantic enforces at model
    # construction. Kept here as defense-in-depth if the model loosens later.
    ("subscriber_dob", "Provide the subscriber's date of birth"),
    ("subscriber_id", "Provide the subscriber/member ID"),
]

_DEPENDENT_FIELDS = [
    "patient_first_name",
    "patient_last_name",
    "patient_dob",
]


class EligibilityDemographicsValidator(BaseValidator):
    """Validates subscriber demographics completeness for eligibility requests."""

    name = "EligibilityDemographicsValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []

        # Check required subscriber fields
        for field_name, suggestion in _REQUIRED_SUBSCRIBER_FIELDS:
            value = getattr(claim, field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                findings.append(
                    self._make_finding(
                        code="ELIG_MISSING_FIELD",
                        message=f"Required field '{field_name}' is missing or empty",
                        severity=Severity.ERROR,
                        field_name=field_name,
                        suggestion=suggestion,
                    )
                )

        # Check dependent info if relationship_code is not "self"
        if claim.relationship_code and claim.relationship_code.lower() != "self":
            missing_dependent: list[str] = []
            for f in _DEPENDENT_FIELDS:
                val = getattr(claim, f)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing_dependent.append(f)
            if missing_dependent:
                findings.append(
                    self._make_finding(
                        code="ELIG_MISSING_DEPENDENT_INFO",
                        message=(
                            "Dependent/patient information required when "
                            "relationship is not 'self'"
                        ),
                        severity=Severity.ERROR,
                        field_name="relationship_code",
                        suggestion=(
                            "Provide patient_first_name, patient_last_name, "
                            "and patient_dob for dependents"
                        ),
                        context={"missing_fields": missing_dependent},
                    )
                )

        return self._make_output(findings)
