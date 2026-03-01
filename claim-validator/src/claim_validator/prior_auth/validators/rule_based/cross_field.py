"""PACrossFieldValidator — cross-field consistency checks for PA requests."""

from __future__ import annotations

from datetime import date

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# Gender-specific CPT ranges (simplified heuristic, not clinical engine)
_FEMALE_ONLY_CPT_RANGES = [
    (59000, 59899),  # OB/Maternity
]
_MALE_ONLY_CPT_RANGES = [
    (55700, 55899),  # Prostate / male reproductive
]


def _cpt_in_ranges(code: str, ranges: list[tuple[int, int]]) -> bool:
    """Check if a numeric CPT code falls within any of the given ranges."""
    try:
        num = int(code)
    except (ValueError, TypeError):
        return False
    return any(lo <= num <= hi for lo, hi in ranges)


def _calculate_age(dob: date) -> int:
    """Calculate age in years from date of birth."""
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class PACrossFieldValidator(BaseValidator):
    """Validates cross-field consistency on PA requests.

    Checks:
    - Diagnosis codes present when procedures are requested
    - Gender compatibility with gender-specific procedures
    - Age compatibility with age-restricted procedures
    """

    name = "PACrossFieldValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []

        self._check_dx_procedure_mismatch(request, findings)
        self._check_demographic_procedure_mismatch(request, findings)

        return self._make_output(findings)

    def _check_dx_procedure_mismatch(
        self,
        request: object,
        findings: list[Finding],
    ) -> None:
        """Check that diagnosis codes are present when procedures exist."""
        if not request.service_lines:  # type: ignore[union-attr]
            return

        if not request.diagnosis_codes:  # type: ignore[union-attr]
            findings.append(
                self._make_finding(
                    code="PA_DX_PROCEDURE_MISMATCH",
                    message=(
                        "Procedure codes in 'service_lines' require at least "
                        "one supporting diagnosis in 'diagnosis_codes'"
                    ),
                    severity=Severity.WARNING,
                    field_name="diagnosis_codes",
                    suggestion=(
                        "Verify clinical appropriateness — add at least one "
                        "ICD-10 diagnosis code that supports the requested "
                        "procedure(s)"
                    ),
                )
            )

    def _check_demographic_procedure_mismatch(
        self,
        request: object,
        findings: list[Finding],
    ) -> None:
        """Check gender and age compatibility with procedures."""
        patient = getattr(request, "patient", None)
        gender = getattr(patient, "gender", None) if patient else None
        gender_upper = gender.upper() if gender is not None else None

        # Determine DOB for age check
        dob = None
        if patient and getattr(patient, "dob", None):
            dob = patient.dob
        elif hasattr(request, "subscriber"):
            dob = request.subscriber.dob  # type: ignore[union-attr]

        for idx, line in enumerate(request.service_lines, start=1):  # type: ignore[union-attr]
            code = line.cpt_code.strip() if line.cpt_code else ""
            if not code:
                continue

            # Gender check
            if gender_upper == "M" and _cpt_in_ranges(code, _FEMALE_ONLY_CPT_RANGES):
                findings.append(
                    self._make_finding(
                        code="PA_DEMOGRAPHIC_PROCEDURE_MISMATCH",
                        message=(
                            f"Procedure on service line {idx} may be "
                            "incompatible with patient gender in "
                            "'patient.gender'"
                        ),
                        severity=Severity.WARNING,
                        field_name="patient.gender",
                        line_number=idx,
                        suggestion=(
                            "Verify the procedure is appropriate for the "
                            "patient's gender"
                        ),
                    )
                )
            elif gender_upper == "F" and _cpt_in_ranges(code, _MALE_ONLY_CPT_RANGES):
                findings.append(
                    self._make_finding(
                        code="PA_DEMOGRAPHIC_PROCEDURE_MISMATCH",
                        message=(
                            f"Procedure on service line {idx} may be "
                            "incompatible with patient gender in "
                            "'patient.gender'"
                        ),
                        severity=Severity.WARNING,
                        field_name="patient.gender",
                        line_number=idx,
                        suggestion=(
                            "Verify the procedure is appropriate for the "
                            "patient's gender"
                        ),
                    )
                )

            # Age check — pediatric codes for adult
            if dob is not None:
                age = _calculate_age(dob)
                # Pediatric well-visit codes (99381-99385 new patient,
                # 99391-99395 established) are for patients <=17
                try:
                    code_num = int(code)
                except (ValueError, TypeError):
                    continue

                is_pediatric = (99381 <= code_num <= 99385) or (
                    99391 <= code_num <= 99395
                )
                if is_pediatric and age > 17:
                    findings.append(
                        self._make_finding(
                            code="PA_DEMOGRAPHIC_PROCEDURE_MISMATCH",
                            message=(
                                f"Procedure on service line {idx} may be "
                                "incompatible with patient age derived from "
                                "'subscriber.dob' or 'patient.dob'"
                            ),
                            severity=Severity.WARNING,
                            field_name="subscriber.dob",
                            line_number=idx,
                            suggestion=(
                                "Verify the procedure is appropriate for the "
                                "patient's age"
                            ),
                        )
                    )
