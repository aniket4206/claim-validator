"""PADiagnosisValidator — ICD-10 diagnosis code validation for PA requests."""

from __future__ import annotations

import re

from claim_validator.code_tables import lookup_icd10
from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_ICD10_PATTERN = re.compile(r"^[A-Za-z]\d{2}(\.\d{1,4}|\d{1,4})?$")


class PADiagnosisValidator(BaseValidator):
    """Validates ICD-10 diagnosis codes on PA requests."""

    name = "PADiagnosisValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []

        if not request.diagnosis_codes:
            return self._make_output(findings)

        for i, code in enumerate(request.diagnosis_codes, start=1):
            code_stripped = code.strip() if code else ""
            if not code_stripped:
                continue

            # Format check
            if not _ICD10_PATTERN.match(code_stripped):
                findings.append(
                    self._make_finding(
                        code="PA_INVALID_DIAGNOSIS_FORMAT",
                        message=(
                            f"Diagnosis code at position {i} in "
                            "'diagnosis_codes' has invalid ICD-10-CM format"
                        ),
                        severity=Severity.ERROR,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "ICD-10-CM codes must start with a letter "
                            "followed by 2+ digits (e.g., J06.9)"
                        ),
                    )
                )
                continue

            # Code table lookup
            if lookup_icd10(code_stripped) is None:
                findings.append(
                    self._make_finding(
                        code="PA_INVALID_DIAGNOSIS",
                        message=(
                            f"Diagnosis code at position {i} in "
                            "'diagnosis_codes' not found in bundled ICD-10-CM table"
                        ),
                        severity=Severity.ERROR,
                        field_name="diagnosis_codes",
                        suggestion="Verify the ICD-10-CM code against the current CMS code set",
                    )
                )

        return self._make_output(findings)
