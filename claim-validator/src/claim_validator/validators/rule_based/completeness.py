"""CompletenessValidator — required CMS-1500 field presence checks."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# Required claim-level string fields: (attribute_name, suggestion)
_REQUIRED_CLAIM_FIELDS: list[tuple[str, str]] = [
    ("billing_provider_npi", "Billing provider NPI is required (CMS-1500 Box 33a)"),
    ("subscriber_id", "Subscriber/insurance ID is required (CMS-1500 Box 1a)"),
    ("patient_first_name", "Patient first name is required (CMS-1500 Box 2)"),
    ("patient_last_name", "Patient last name is required (CMS-1500 Box 2)"),
    ("patient_dob", "Patient date of birth is required (CMS-1500 Box 3)"),
    ("patient_gender", "Patient gender is required (CMS-1500 Box 3)"),
    ("payer_id", "Payer ID is required (CMS-1500 Box 11)"),
]


class CompletenessValidator(BaseValidator):
    """Validates that all required CMS-1500 fields are present and non-empty."""

    name = "CompletenessValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        # Check required claim-level string fields
        for field_name, suggestion in _REQUIRED_CLAIM_FIELDS:
            value = getattr(claim, field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                findings.append(
                    self._make_finding(
                        code="MISSING_FIELD",
                        message=f"Required field '{field_name}' is missing or empty",
                        severity=Severity.ERROR,
                        field_name=field_name,
                        suggestion=suggestion,
                    )
                )

        # Check diagnosis_codes is non-empty
        if not claim.diagnosis_codes:
            findings.append(
                self._make_finding(
                    code="MISSING_FIELD",
                    message="At least one diagnosis code is required",
                    severity=Severity.ERROR,
                    field_name="diagnosis_codes",
                    suggestion="Add at least one ICD-10 diagnosis code (CMS-1500 Box 21)",
                )
            )

        # Check lines is non-empty
        if not claim.lines:
            findings.append(
                self._make_finding(
                    code="MISSING_FIELD",
                    message="At least one service line is required",
                    severity=Severity.ERROR,
                    field_name="lines",
                    suggestion="Add at least one service line (CMS-1500 Box 24)",
                )
            )

        # Check required line-level fields
        for idx, line in enumerate(claim.lines, start=1):
            if not line.diagnosis_pointers:
                findings.append(
                    self._make_finding(
                        code="MISSING_FIELD",
                        message="Service line is missing diagnosis pointers",
                        severity=Severity.ERROR,
                        field_name="diagnosis_pointers",
                        line_number=idx,
                        suggestion="Link at least one diagnosis to this line (CMS-1500 Box 24E)",
                    )
                )

            if not line.service_date_from or (
                isinstance(line.service_date_from, str) and not line.service_date_from.strip()
            ):
                findings.append(
                    self._make_finding(
                        code="MISSING_FIELD",
                        message="Service line is missing service date",
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion="Provide a service date for this line (CMS-1500 Box 24A)",
                    )
                )

        return self._make_output(findings)
