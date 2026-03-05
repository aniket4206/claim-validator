"""DemographicsValidator — patient demographics consistency.

Delegates DOB + gender checks to ``shared.validators.validate_demographics``.
Self-relationship mismatch check remains domain-specific.
"""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.validators import validate_demographics
from claim_validator.validators.base import BaseValidator


class DemographicsValidator(BaseValidator):
    """Validates patient demographics consistency."""

    name = "DemographicsValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        # Delegate DOB + gender to shared pure function
        shared_findings = validate_demographics(
            name=claim.patient_first_name,  # pass to avoid false MISSING_PATIENT_NAME
            gender=claim.patient_gender,
            dob=claim.patient_dob,
            field_prefix="patient_",
        )
        # Filter name-related findings — CompletenessValidator handles required fields
        findings.extend(f for f in shared_findings if f.code != "MISSING_PATIENT_NAME")

        # Domain-specific cross-field check
        self._check_self_relationship(claim, findings)

        return self._make_output(findings)

    def _check_self_relationship(self, claim: ClaimData, findings: list[Finding]) -> None:
        rel = claim.patient_relationship
        if not rel or rel.strip().lower() != "self":
            return  # Only check when relationship is "self"

        # Need subscriber names to compare
        sub_first = claim.subscriber_first_name
        sub_last = claim.subscriber_last_name
        pat_first = claim.patient_first_name
        pat_last = claim.patient_last_name

        if not sub_first or not sub_last:
            return  # Can't compare if subscriber names aren't provided

        if not pat_first or not pat_last:
            return  # Can't compare if patient names aren't provided

        # Case-insensitive comparison
        first_match = sub_first.strip().lower() == pat_first.strip().lower()
        last_match = sub_last.strip().lower() == pat_last.strip().lower()

        if not (first_match and last_match):
            findings.append(
                self._make_finding(
                    code="SELF_RELATIONSHIP_MISMATCH",
                    message=(
                        "Patient relationship is 'self' but subscriber"
                        " and patient names differ"
                    ),
                    severity=Severity.WARNING,
                    field_name="patient_relationship",
                    suggestion=(
                        "When relationship is 'self', subscriber and patient"
                        " should be the same person (CMS-1500 Box 6)"
                    ),
                )
            )
