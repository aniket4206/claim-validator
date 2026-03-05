"""CodingValidator — diagnosis/procedure code validation.

Delegates ICD-10 + CPT/HCPCS format/lookup to shared pure functions.
Modifier checks, diagnosis pointer, and unreferenced-diagnosis checks
remain domain-specific.
"""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.validators import validate_diagnosis, validate_procedure
from claim_validator.validators.base import BaseValidator

_MODIFIER_PATTERN = re.compile(r"^[A-Za-z0-9]{2}$")

# Shared → domain code remapping tables
_DX_CODE_MAP = {
    "INVALID_DIAGNOSIS_FORMAT": "INVALID_DIAGNOSIS_CODE_FORMAT",
    "INVALID_DIAGNOSIS": "INVALID_DIAGNOSIS_CODE",
}
_PX_CODE_MAP = {
    "INVALID_PROCEDURE_FORMAT": "INVALID_PROCEDURE_CODE_FORMAT",
    "INVALID_PROCEDURE": "INVALID_PROCEDURE_CODE",
}


class CodingValidator(BaseValidator):
    """Validates diagnosis codes, procedure codes, modifiers,
    and diagnosis pointer consistency."""

    name = "CodingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_diagnosis_codes(claim, findings)
        self._check_procedure_codes(claim, findings)
        self._check_modifiers(claim, findings)
        self._check_diagnosis_pointers(claim, findings)
        self._check_unreferenced_diagnoses(claim, findings)

        return self._make_output(findings)

    def _check_diagnosis_codes(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes:
            return

        codes = [dx.code.strip() if dx.code else "" for dx in claim.diagnosis_codes]
        codes = [c for c in codes if c]  # skip empty — CompletenessValidator handles

        shared_findings = validate_diagnosis(codes, field_name="diagnosis_codes")
        for f in shared_findings:
            new_code = _DX_CODE_MAP.get(f.code, f.code)
            if new_code != f.code:
                findings.append(f.model_copy(update={"code": new_code}))
            else:
                findings.append(f)

    def _check_procedure_codes(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        for idx, line in enumerate(claim.lines, start=1):
            code = line.procedure_code.strip()
            if not code:
                continue

            shared_findings = validate_procedure(
                [code], field_name="procedure_code",
            )
            for f in shared_findings:
                new_code = _PX_CODE_MAP.get(f.code, f.code)
                update: dict = {"line_number": idx}
                if new_code != f.code:
                    update["code"] = new_code
                # Claims treats unknown procedures as ERROR (shared uses WARNING)
                if f.severity == Severity.WARNING:
                    update["severity"] = Severity.ERROR
                findings.append(f.model_copy(update=update))

    def _check_modifiers(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        for idx, line in enumerate(claim.lines, start=1):
            for mod in line.modifiers:
                mod_stripped = mod.strip() if mod else ""
                if not mod_stripped:
                    continue

                if not _MODIFIER_PATTERN.match(mod_stripped):
                    findings.append(
                        self._make_finding(
                            code="INVALID_MODIFIER_FORMAT",
                            message=(
                                "Modifier in 'modifiers' must"
                                " be exactly 2 alphanumeric"
                                " characters"
                            ),
                            severity=Severity.ERROR,
                            field_name="modifiers",
                            line_number=idx,
                            suggestion=(
                                "Modifiers are 2-character"
                                " codes (e.g., 25, 59, TC)"
                            ),
                        )
                    )

    def _check_diagnosis_pointers(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes or not claim.lines:
            return

        valid_pointers = {
            dx.pointer for dx in claim.diagnosis_codes
        }

        for idx, line in enumerate(claim.lines, start=1):
            for ptr in line.diagnosis_pointers:
                if ptr not in valid_pointers:
                    findings.append(
                        self._make_finding(
                            code="INVALID_DIAGNOSIS_POINTER",
                            message=(
                                "Diagnosis pointer in"
                                " 'diagnosis_pointers'"
                                " references a non-existent"
                                " diagnosis position"
                            ),
                            severity=Severity.ERROR,
                            field_name="diagnosis_pointers",
                            line_number=idx,
                            suggestion=(
                                "Each diagnosis pointer must"
                                " reference a valid pointer"
                                " value in the claim's"
                                " diagnosis codes"
                            ),
                        )
                    )

    def _check_unreferenced_diagnoses(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes or not claim.lines:
            return

        referenced_pointers: set[int] = set()
        for line in claim.lines:
            referenced_pointers.update(line.diagnosis_pointers)

        for dx in claim.diagnosis_codes:
            if dx.pointer not in referenced_pointers:
                findings.append(
                    self._make_finding(
                        code="UNREFERENCED_DIAGNOSIS",
                        message=(
                            "Diagnosis code in"
                            " 'diagnosis_codes' is not"
                            " referenced by any service"
                            " line"
                        ),
                        severity=Severity.WARNING,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "Each diagnosis code should be"
                            " referenced by at least one"
                            " service line via"
                            " diagnosis_pointers"
                        ),
                    )
                )
