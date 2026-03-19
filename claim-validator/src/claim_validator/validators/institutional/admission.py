"""Admission validator for institutional (UB-04) claims."""

from __future__ import annotations

from datetime import date
from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# Valid UB-04 admission type codes
_VALID_ADMISSION_TYPES = {"1", "2", "3", "4", "5", "9"}
# Valid admission source codes
_VALID_ADMISSION_SOURCES = {"1", "2", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"}
# Valid patient status codes (01-66, plus 69, 70, 87, etc.)
_VALID_PATIENT_STATUSES = {
    "01", "02", "03", "04", "05", "06", "07", "08", "09",
    "20", "21", "30", "40", "41", "42", "43", "50", "51",
    "61", "62", "63", "64", "65", "66", "69", "70", "81",
    "82", "83", "84", "85", "86", "87", "88", "89", "90",
    "91", "92", "93", "94", "95",
}


class AdmissionValidator(BaseValidator):
    """Validates admission data on institutional claims."""

    name = "AdmissionValidator"

    def validate(self, claim: Any) -> ValidatorOutput:  # type: ignore[override]
        """Validate admission fields on an institutional claim."""
        findings: list[Finding] = []

        admission_date = getattr(claim, "admission_date", None)
        discharge_date = getattr(claim, "discharge_date", None)

        # Validate admission_date <= discharge_date
        if admission_date and discharge_date:
            try:
                adm = date.fromisoformat(str(admission_date))
                dis = date.fromisoformat(str(discharge_date))
                if adm > dis:
                    findings.append(self._make_finding(
                        code="INST_ADMISSION_DATE_ORDER",
                        message="Admission date is after discharge date",
                        severity=Severity.ERROR,
                        field_name="admission_date",
                    ))
            except ValueError:
                pass  # Date format issues handled elsewhere

        # Validate admission_type_code
        atc = getattr(claim, "admission_type_code", None)
        if atc is not None and str(atc).strip() not in _VALID_ADMISSION_TYPES:
            findings.append(self._make_finding(
                code="INST_ADMISSION_INVALID_TYPE",
                message=f"Invalid admission type code: '{atc}'",
                severity=Severity.ERROR,
                field_name="admission_type_code",
                suggestion=f"Valid codes: {', '.join(sorted(_VALID_ADMISSION_TYPES))}",
            ))

        # Validate admission_source_code
        asc = getattr(claim, "admission_source_code", None)
        if asc is not None and str(asc).strip() not in _VALID_ADMISSION_SOURCES:
            findings.append(self._make_finding(
                code="INST_ADMISSION_INVALID_SOURCE",
                message=f"Invalid admission source code: '{asc}'",
                severity=Severity.ERROR,
                field_name="admission_source_code",
                suggestion=f"Valid codes: {', '.join(sorted(_VALID_ADMISSION_SOURCES))}",
            ))

        # Validate patient_status_code
        psc = getattr(claim, "patient_status_code", None)
        if psc is not None and str(psc).strip().zfill(2) not in _VALID_PATIENT_STATUSES:
            findings.append(self._make_finding(
                code="INST_ADMISSION_INVALID_STATUS",
                message=f"Invalid patient status code: '{psc}'",
                severity=Severity.ERROR,
                field_name="patient_status_code",
            ))

        return self._make_output(findings)
