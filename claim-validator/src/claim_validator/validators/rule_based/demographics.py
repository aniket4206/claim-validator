"""DemographicsValidator — patient demographics consistency."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_VALID_GENDERS = {"M", "F", "U"}


class DemographicsValidator(BaseValidator):
    """Validates patient demographics consistency."""

    name = "DemographicsValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_dob(claim, findings)
        self._check_gender(claim, findings)
        self._check_self_relationship(claim, findings)

        return self._make_output(findings)

    def _check_dob(self, claim: ClaimData, findings: list[Finding]) -> None:
        dob = claim.patient_dob
        if not dob or not dob.strip():
            return  # CompletenessValidator handles required

        try:
            dob_date = datetime.date.fromisoformat(dob.strip())
        except ValueError:
            findings.append(
                self._make_finding(
                    code="INVALID_DOB_FORMAT",
                    message="Field 'patient_dob' must be a valid date in YYYY-MM-DD format",
                    severity=Severity.ERROR,
                    field_name="patient_dob",
                    suggestion="Provide date of birth in YYYY-MM-DD format (CMS-1500 Box 3)",
                )
            )
            return  # Can't check future if format is invalid

        if dob_date > datetime.date.today():
            findings.append(
                self._make_finding(
                    code="FUTURE_DOB",
                    message="Field 'patient_dob' is in the future",
                    severity=Severity.ERROR,
                    field_name="patient_dob",
                    suggestion="Verify the patient date of birth (CMS-1500 Box 3)",
                )
            )

    def _check_gender(self, claim: ClaimData, findings: list[Finding]) -> None:
        gender = claim.patient_gender
        if not gender or not gender.strip():
            return  # CompletenessValidator handles required

        if gender.strip().upper() not in _VALID_GENDERS:
            findings.append(
                self._make_finding(
                    code="INVALID_GENDER",
                    message="Field 'patient_gender' must be one of: M, F, U",
                    severity=Severity.ERROR,
                    field_name="patient_gender",
                    suggestion=(
                        "Use M (male), F (female), or U (unknown)"
                        " for patient gender (CMS-1500 Box 3)"
                    ),
                )
            )

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
