"""PADiagnosisValidator — ICD-10 diagnosis code validation for PA requests.

Thin wrapper around ``shared.validators.validate_diagnosis``.
"""

from __future__ import annotations

from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_diagnosis
from claim_validator.validators.base import BaseValidator


class PADiagnosisValidator(BaseValidator):
    """Validates ICD-10 diagnosis codes on PA requests."""

    name = "PADiagnosisValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_diagnosis(
            request.diagnosis_codes, field_name="diagnosis_codes", code_prefix="PA_",
        )
        # Remap messages to include position (tests expect "position N" in message)
        findings = []
        for f in shared_findings:
            pos = f.context.get("position") if f.context else None
            if pos is not None and f.code == "PA_INVALID_DIAGNOSIS_FORMAT":
                findings.append(f.model_copy(update={
                    "message": (
                        f"Diagnosis code at position {pos} in "
                        "'diagnosis_codes' has invalid ICD-10-CM format"
                    ),
                }))
            elif pos is not None and f.code == "PA_INVALID_DIAGNOSIS":
                findings.append(f.model_copy(update={
                    "message": (
                        f"Diagnosis code at position {pos} in "
                        "'diagnosis_codes' not found in bundled ICD-10-CM table"
                    ),
                }))
            else:
                findings.append(f)
        return self._make_output(findings)
